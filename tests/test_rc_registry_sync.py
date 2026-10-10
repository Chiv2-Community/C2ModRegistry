import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/scripts/sync-rc-registry.sh"
)
WORKFLOWS = SCRIPT.parent.parent


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

    def dispatch(self, **overrides):
        # Execute the exact producer run command with the workflow's output contract.
        workflow = (WORKFLOWS / "add-release-from-issue.yml").read_text()
        step = workflow.split("- name: Dispatch RC sync after a release commit\n")[1].split("\n      - name:")[0]
        contracts = {
            "GH_TOKEN": "secrets.GITHUB_TOKEN",
            "REGISTRY_ACTION": "needs.parse-json.outputs.action",
            "REGISTRY_FAILED": "steps.update-package-list.outputs.failed",
            "COMMIT_OUTCOME": "steps.commit-registry.outcome",
            "CHANGES_DETECTED": "steps.commit-registry.outputs.changes_detected",
            "SOURCE_BRANCH": "steps.branch-name.outputs.branch_name",
            "SOURCE_SHA": "steps.commit-registry.outputs.commit_hash",
        }
        for key, expression in contracts.items():
            self.assertIn(f"{key}: ${{{{ {expression} }}}}", step)
        self.assertIn("id: commit-registry", workflow.split("- name: Commit changes\n")[1].split("- name: Dispatch")[0])
        for permission in ("actions", "contents", "issues", "pull-requests"):
            self.assertIn(f"      {permission}: write", workflow)
        command = step.split("run: ")[1].strip()
        script_path = command.split(" ", 1)[1]
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        log = self.root / "dispatch.json"
        mock = bin_dir / "gh"
        mock.write_text("#!/usr/bin/env python3\nimport json,os,sys\n"
                        "open(os.environ['DISPATCH_LOG'],'w').write(json.dumps(sys.argv[1:]))\n"
                        "sys.exit(int(os.environ.get('DISPATCH_EXIT','0')))\n")
        mock.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                   DISPATCH_LOG=str(log), GITHUB_REPOSITORY="test/registry",
                   GITHUB_REF="refs/heads/main", GH_TOKEN="test-token",
                   REGISTRY_ACTION="add-package-release", REGISTRY_FAILED="false",
                   COMMIT_OUTCOME="success", CHANGES_DETECTED="true",
                   SOURCE_BRANCH="main", SOURCE_SHA=self.git("rev-parse", "HEAD").stdout.strip())
        env.update(overrides)
        result = subprocess.run(["bash", str(WORKFLOWS.parent.parent / script_path)],
                                cwd=self.repo, env=env, text=True, capture_output=True)
        return result, json.loads(log.read_text()) if log.exists() else None

    def test_release_bot_commit_and_retry_handoff_reach_receiver(self):
        for name in ("issue", "retry"):
            with self.subTest(name=name):
                self.git("checkout", "main")
                source = self.commit(f"{name}.txt", f"{name}\n")
                self.git("push", "origin", "main")
                result, args = self.dispatch()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(args, ["api", "--method", "POST",
                    "repos/test/registry/actions/workflows/sync-rc-registry.yml/dispatches",
                    "-f", "ref=main", "-f", "inputs[source_branch]=main",
                    "-f", f"inputs[source_sha]={source}"])
                self.sync(env=dict(os.environ, SOURCE_BRANCH="main", SOURCE_SHA=source,
                                   GITHUB_REF="refs/heads/main"))
                self.assertEqual(self.destination(), source)
                (self.root / "dispatch.json").unlink()

    def test_failed_noop_and_package_producers_do_not_dispatch(self):
        for overrides in ({"REGISTRY_FAILED": "true"}, {"REGISTRY_FAILED": ""},
                          {"COMMIT_OUTCOME": "failure"}, {"COMMIT_OUTCOME": "skipped"},
                          {"CHANGES_DETECTED": "false"},
                          {"REGISTRY_ACTION": "add-package", "SOURCE_BRANCH": "issue-1-add-package"}):
            with self.subTest(overrides=overrides):
                result, args = self.dispatch(**overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNone(args)

    def test_dispatch_rejects_wrong_branch_ref_or_nonimmutable_source(self):
        for overrides in ({"SOURCE_BRANCH": "issue-1-add-package"}, {"SOURCE_SHA": "main"},
                          {"SOURCE_SHA": "0" * 40}, {"GITHUB_REF": "refs/heads/other"}):
            with self.subTest(overrides=overrides):
                result, args = self.dispatch(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(args)
        old = self.git("rev-parse", "HEAD").stdout.strip()
        self.commit("new.txt", "new\n")
        self.git("push", "origin", "main")
        result, args = self.dispatch(SOURCE_SHA=old)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(args)
        self.git("checkout", "-b", "package")
        package = self.commit("unapproved.txt", "unapproved\n")
        self.git("push", "origin", "package")
        result, args = self.dispatch(SOURCE_SHA=package)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(args)

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

    def test_dispatch_failure_is_not_reported_as_success(self):
        result, args = self.dispatch(DISPATCH_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(args)

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
