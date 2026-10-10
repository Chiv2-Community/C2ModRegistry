import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/scripts/sync-rc-registry.sh"
)


class RcRegistrySyncTests(unittest.TestCase):
    def setUp(self):
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
        self.sync()
        destination = self.destination()
        self.git("merge-base", "--is-ancestor", compatibility, destination)
        self.git("merge-base", "--is-ancestor", source, destination)
        self.assertEqual((self.repo / "compatibility.txt").read_text(), "keep\n")
        self.sync()
        self.assertEqual(self.destination(), destination)

    def test_conflict_does_not_push_and_aborts_merge(self):
        self.git("checkout", "update-registry-format")
        compatibility = self.commit("shared.txt", "compatibility\n")
        self.git("push", "origin", "update-registry-format")
        self.git("checkout", "main")
        self.commit("shared.txt", "main\n")
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

    def test_stale_snapshot_cannot_regress_compatibility_branch(self):
        old = self.commit("old.txt", "old\n")
        latest = self.commit("latest.txt", "latest\n")
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


if __name__ == "__main__":
    unittest.main()
