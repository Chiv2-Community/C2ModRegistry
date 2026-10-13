"""Keep every issue registration on the same validated PR-only path."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/add-release-from-issue.yml").read_text()


def step(name):
    return WORKFLOW.split("      - name: " + name + "\n", 1)[1].split("\n      - name:", 1)[0]


class ReleaseApprovalTests(unittest.TestCase):
    def test_only_explicit_release_actions_and_tags_are_accepted(self):
        script = textwrap.dedent(step("Validate JSON payload").split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            for action in ("add-package-release", "add-dll-release", "add-package", "process-registry-updates", "validate"):
                for tag in ("v1.0.0", "", None, 123):
                    with self.subTest(action=action, tag=tag):
                        payload = {"action": action, "repo_url": "https://github.com/Test/Plugin", "release_tag": tag}
                        result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                            env=dict(os.environ, PAYLOAD=json.dumps(payload), GITHUB_OUTPUT=directory + "/outputs",
                                     GITHUB_STEP_SUMMARY=directory + "/summary"), capture_output=True, text=True)
                        self.assertEqual(result.returncode == 0, action in ("add-package-release", "add-dll-release") and tag == "v1.0.0", result.stderr)

    def test_every_registration_creates_an_issue_branch_pr_after_validation(self):
        publication = step("Create pull request")
        self.assertIn("uses: peter-evans/create-pull-request@v7", publication)
        self.assertIn("if: steps.update-package-list.outputs.failed == 'false' && steps.validate-release.outputs.failed == 'false'", publication)
        self.assertIn("base: main", publication)
        self.assertIn("branch: issue-${{ github.event.issue.number }}-${{ needs.parse-json.outputs.action }}", publication)
        self.assertIn("Resolves #${{ github.event.issue.number }}", publication)
        self.assertIn("${{ fromJson(needs.parse-json.outputs.json_payload).release_tag }}", publication)
        self.assertNotIn("outputs.action ==", publication)
        self.assertNotIn("outputs.action !=", publication)
        self.assertNotIn("git-auto-commit-action", WORKFLOW)
        self.assertNotIn("gh issue close", WORKFLOW)
        self.assertNotIn("dispatch-rc-registry-sync", WORKFLOW)
        self.assertNotIn("actions: write", WORKFLOW)
        self.assertIn("steps.release-pr.outputs.pull-request-number != ''", step("Post success results"))
        self.assertIn("cancel-in-progress: false", WORKFLOW)

    def test_validation_is_read_only_in_pr_ci(self):
        ci = (ROOT / ".github/workflows/pull-request-ci.yml").read_text()
        self.assertNotIn("process-registry-updates", ci)
        self.assertNotIn("git-auto-commit-action", ci)
        self.assertIn("command: validate", ci)
