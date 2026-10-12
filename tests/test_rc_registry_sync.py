import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/scripts/sync-rc-registry.sh"
)
WORKFLOWS = SCRIPT.parent.parent


class RcRegistrySyncTests(unittest.TestCase):
    def setUp(self):
        # These local repositories model a main event, not the enclosing PR CI ref.
        event = mock.patch.dict(os.environ, {"GITHUB_REF": "refs/heads/main"})
        event.start()
        self.addCleanup(event.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "--bare", str(self.remote))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("remote", "add", "origin", str(self.remote))
        self.commit("shared.txt", "base\n")
        self.git("branch", "update-registry-format")
        self.git("push", "origin", "main", "update-registry-format")

    def git(self, *args, check=True):
        return subprocess.run(
            ["git", *args], cwd=self.repo, text=True,
            capture_output=True, check=check,
        )

    def commit(self, path, content):
        (self.repo / path).write_text(content)
        self.git("add", path)
        self.git("commit", "-m", f"Update {path}")
        return self.git("rev-parse", "HEAD").stdout.strip()

    def destination(self):
        return self.git(
            "ls-remote", "origin", "refs/heads/update-registry-format"
        ).stdout.split()[0]

    def sync(self, check=True, env=None):
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=self.repo, text=True,
            capture_output=True, check=check, env=env,
        )

    def test_main_advances_and_repeated_sync_is_noop(self):
        first = self.commit("first.txt", "first\n")
        self.git("push", "origin", "main")
        self.sync()
        self.assertEqual(self.destination(), first)
        self.sync()
        self.assertEqual(self.destination(), first)
        self.git("checkout", "main")
        second = self.commit("second.txt", "second\n")
        self.git("push", "origin", "main")
        self.sync()
        self.assertEqual(self.destination(), second)
        self.assertEqual(self.git("rev-parse", "main").stdout.strip(), second)

    def test_divergence_is_merged_without_losing_destination_commits(self):
        self.git("checkout", "update-registry-format")
        compatibility = self.commit("compatibility.txt", "keep\n")
        self.git("push", "origin", "update-registry-format")
        self.git("checkout", "main")
        source = self.commit("main.txt", "new\n")
        self.git("push", "origin", "main")
        self.sync()
        destination = self.destination()
        self.git("merge-base", "--is-ancestor", compatibility, destination)
        self.git("merge-base", "--is-ancestor", source, destination)
        self.assertEqual((self.repo / "compatibility.txt").read_text(), "keep\n")
        self.sync(env=dict(os.environ, SOURCE_SHA=source))
        self.assertEqual(self.destination(), destination)

    def test_conflict_does_not_push_and_aborts_merge(self):
        self.git("checkout", "update-registry-format")
        compatibility = self.commit("shared.txt", "compatibility\n")
        self.git("push", "origin", "update-registry-format")
        self.git("checkout", "main")
        self.commit("shared.txt", "main\n")
        self.git("push", "origin", "main")
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.destination(), compatibility)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        self.assertNotEqual(self.git("rev-parse", "--verify", "MERGE_HEAD", check=False).returncode, 0)

    def test_source_is_checked_out_snapshot_not_latest_remote_main(self):
        snapshot = self.commit("snapshot.txt", "snapshot\n")
        latest = self.commit("later.txt", "later\n")
        self.git("push", "origin", "main")
        self.git("checkout", "--detach", snapshot)
        self.sync()
        self.assertEqual(self.destination(), snapshot)
        self.assertEqual(self.git("rev-parse", "main").stdout.strip(), latest)

    def test_dispatch_input_is_snapshot_not_receiver_checkout_or_latest_main(self):
        snapshot = self.commit("snapshot.txt", "snapshot\n")
        latest = self.commit("later.txt", "later\n")
        self.git("push", "origin", "main")
        self.sync(env=dict(os.environ, SOURCE_SHA=snapshot, SOURCE_BRANCH="main"))
        self.assertEqual(self.destination(), snapshot)
        self.assertEqual(self.git("rev-parse", "main").stdout.strip(), latest)

    def test_stale_snapshot_cannot_regress_compatibility_branch(self):
        old = self.commit("old.txt", "old\n")
        latest = self.commit("latest.txt", "latest\n")
        self.git("push", "origin", "main")
        self.sync()
        self.git("checkout", "--detach", old)
        self.sync()
        self.assertEqual(self.destination(), latest)

    def test_missing_destination_fails_without_creating_it(self):
        self.git("push", "origin", "--delete", "update-registry-format")
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            self.git("ls-remote", "origin", "refs/heads/update-registry-format").stdout,
            "",
        )

    def test_concurrent_destination_update_is_not_overwritten(self):
        self.git("checkout", "update-registry-format")
        concurrent = self.commit("concurrent.txt", "keep concurrent update\n")
        self.git("checkout", "main")
        self.commit("main.txt", "new\n")
        self.git("push", "origin", "main")
        # Make the concurrent commit available remotely without moving the destination yet.
        self.git("push", "origin", f"{concurrent}:refs/heads/concurrent")
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text(
            '#!/usr/bin/env bash\n'
            'git --git-dir="$TEST_REMOTE" update-ref '
            'refs/heads/update-registry-format "$TEST_CONCURRENT"\n'
        )
        hook.chmod(0o755)
        env = dict(os.environ, TEST_REMOTE=str(self.remote), TEST_CONCURRENT=concurrent)
        result = self.sync(check=False, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.destination(), concurrent)

    def test_receiver_rejects_unapproved_or_mutable_sources_before_writes(self):
        before = self.destination()
        self.git("checkout", "-b", "package")
        package = self.commit("unapproved.txt", "unapproved\n")
        self.git("push", "origin", "package")
        for overrides in ({"SOURCE_SHA": package}, {"SOURCE_SHA": "main"},
                          {"SOURCE_BRANCH": "package"}, {"GITHUB_REF": "refs/heads/package"}):
            result = self.sync(check=False, env=dict(os.environ, **overrides))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.destination(), before)

    def test_receiver_event_and_serialization_contract(self):
        workflow = (WORKFLOWS / "sync-rc-registry.yml").read_text()
        for contract in ("branches: [main]", "workflow_dispatch:",
                         "if: github.ref == 'refs/heads/main'",
                         "group: sync-rc-registry", "cancel-in-progress: false",
                         "ref: ${{ github.sha }}", "fetch-depth: 0",
                         "SOURCE_BRANCH: ${{ inputs.source_branch || 'main' }}",
                         "SOURCE_SHA: ${{ inputs.source_sha || github.sha }}"):
            self.assertIn(contract, workflow)
        self.assertNotIn("push:\n    branches: [update-registry-format]", workflow)


if __name__ == "__main__":
    unittest.main()
