"""Exercise production issue validation and safe asset-name forwarding."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DllIssueRequestTests(unittest.TestCase):
    def test_dll_template_matches_release_template_format(self):
        template = (ROOT / '.github/ISSUE_TEMPLATE/add-dll-release.md').read_text()
        self.assertIn('title: "[DLL RELEASE] PLUGIN_NAME Version PLUGIN_VERSION"', template)
        self.assertIn('- Publish a GitHub release with a semantic version tag', template)
        self.assertIn('Leave `action` unchanged.', template)
        self.assertIn('approval by a registry admin', template)
        self.assertIn('fix the reported error and reply "retry"', template)
        payload = json.loads(template.rsplit('```json\n', 1)[1].split('```', 1)[0])
        self.assertEqual(payload['repo_url'], 'https://github.com/USERNAME/PLUGIN_REPO_NAME')
        self.assertEqual(payload['release_tag'], 'PLUGIN_VERSION')
        self.assertNotIn('DLL plugins do not need', template)
        self.assertIn('Commit `plugin.json` at the repository root before tagging', template)
        self.assertIn('schemas/plugin.schema.json', template)
        self.assertIn('The file in the release assets takes precedence over the file in the repo.', template)
        extracted = subprocess.run(['awk', '/^```/{if (flag) exit; flag=1; next} flag'],
                                   input=template, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(extracted.stdout), payload)

    def test_comments_name_the_correct_database(self):
        workflow = (ROOT / '.github/workflows/add-release-from-issue.yml').read_text()
        for name in ('Confirmation Message', 'Post failure Results '):
            step = workflow.split('      - name: ' + name + '\n', 1)[1].split('\n      - name:', 1)[0]
            self.assertIn("outputs.action == 'add-dll-release' && 'DLL DB' || 'package DB'", step)
        self.assertIn('Created a pull request for approval to add this release to DLL DB.', workflow)

    def test_dll_issue_integrity_validation_is_mandatory_before_publication(self):
        workflow = (ROOT / '.github/workflows/add-release-from-issue.yml').read_text()
        validation = workflow.split('      - name: Validate registry before creating a pull request\n', 1)[1].split('\n      - name:', 1)[0]
        self.assertIn("verify_dll_downloads: 'true'", validation)
        self.assertIn('command: validate', validation)
        self.assertNotIn('json_payload', validation)
        step = workflow.split('      - name: Create pull request\n', 1)[1].split('\n      - name:', 1)[0]
        self.assertIn("steps.validate-release.outputs.failed == 'false'", step)
        self.assertIn("steps.update-package-list.outputs.failed == 'false'", step)
        self.assertIn('uses: peter-evans/create-pull-request@v7', step)
        self.assertNotIn('git-auto-commit-action', workflow)

    def test_wrapper_verifies_downloads_by_default(self):
        action = (ROOT / '.github/actions/registry/action.yml').read_text()
        self.assertIn("verify_dll_downloads:\n    default: 'true'", action)
        script = textwrap.dedent(action.split('      run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            docker = path / 'docker'
            docker.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                              'if sys.argv[1] == "run":\n'
                              '    open(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[2:]))\n')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=directory + ':' + os.environ['PATH'],
                       COMMAND='validate', REPO_URL='', RELEASE_TAG='',
                       RUNNER_TEMP=directory, GITHUB_WORKSPACE=directory,
                       GITHUB_OUTPUT=directory + '/output', CAPTURE=directory + '/args')
            env.pop('VERIFY_DLL_DOWNLOADS', None)
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=directory,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((path / 'args').read_text())[-2:], ['validate', '--verify-dll-downloads'])

    def test_initial_template_omits_filename_and_failure_comment_explains_retry(self):
        template = (ROOT / '.github/ISSUE_TEMPLATE/add-dll-release.md').read_text()
        self.assertNotIn('dll_file', template)
        payload = json.loads(template.rsplit('```json\n', 1)[1].split('```', 1)[0])
        self.assertEqual(set(payload), {'action', 'repo_url', 'release_tag'})
        workflow = (ROOT / '.github/workflows/add-release-from-issue.yml').read_text()
        step = workflow.split('      - name: Explain DLL asset selection after an ambiguous release\n', 1)[1].split('\n      - name:', 1)[0]
        self.assertIn("outputs.failed == 'true'", step)
        self.assertIn("outputs.action == 'add-dll-release'", step)
        self.assertIn('!fromJson(needs.parse-json.outputs.json_payload).dll_file', step)
        self.assertIn('contains(steps.update-package-list.outputs.result', step)
        self.assertIn('"dll_file": "UnchainedPlugin.dll"', step)
        self.assertIn('exact, case-sensitive asset filename', step)
        self.assertIn('retry', step)
        self.assertIn('issue-number: ${{ github.event.issue.number }}', step)

    def test_payload_filename_validation(self):
        workflow = (ROOT / '.github/workflows/add-release-from-issue.yml').read_text()
        step = workflow.split('      - name: Validate JSON payload\n', 1)[1].split('\n      - name:', 1)[0]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            for fields, valid in (({}, True), ({'dll_file': 'Plugin.dll'}, True),
                                  ({'dll_file': 'Plugin debug.dll'}, True),
                                  ({'dll_file': ''}, False), ({'dll_file': None}, False),
                                  ({'dll_file': True}, False), ({'dll_file': ['Plugin.dll']}, False)):
                with self.subTest(fields=fields):
                    result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                        env=dict(os.environ, PAYLOAD=json.dumps(dict(action='add-dll-release', repo_url='https://github.com/Test/Plugin', release_tag='v1.0.0', **fields)),
                                 GITHUB_OUTPUT=directory + '/output', GITHUB_STEP_SUMMARY=directory + '/summary'),
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, valid, result.stderr)

    def test_wrapper_passes_asset_name_as_one_literal_argument(self):
        action = (ROOT / '.github/actions/registry/action.yml').read_text()
        script = textwrap.dedent(action.split('      run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            docker = path / 'docker'
            docker.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                              'if sys.argv[1] == "run":\n'
                              '    open(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[2:]))\n')
            docker.chmod(0o755)
            filename = 'Plugin debug $(touch SHOULD_NOT_EXIST).dll'
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=directory,
                env=dict(os.environ, PATH=directory + ':' + os.environ['PATH'],
                         COMMAND='add-dll-release', REPO_URL='https://github.com/Test/Plugin',
                         RELEASE_TAG='v1.0.0', DLL_FILE=filename,
                         RUNNER_TEMP=directory, GITHUB_WORKSPACE=directory,
                         GITHUB_OUTPUT=directory + '/output', CAPTURE=directory + '/args'),
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads((path / 'args').read_text())
            self.assertEqual(args[-2:], ['--dll-file', filename])
            self.assertFalse((path / 'SHOULD_NOT_EXIST').exists())
