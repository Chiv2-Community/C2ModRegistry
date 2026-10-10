"""Exercise the patched Docker CLI and the exact composite action shell.

Only remote metadata retrieval is replaced with deterministic fixtures; registry
loading, validation, processing, index writes, CLI exits and Docker are real.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github/actions/registry"
REVISION = "5577c4c3f5870f192c4929eaecc11ae6d7becf77"
IMAGE = f"zero-infra-mod-registry:{REVISION}-" + hashlib.sha256(
    (ACTION / "upstream.patch").read_bytes()
).hexdigest()
# Extract rather than copy the production shell, so tests cannot drift from CI.
ACTION_SHELL = textwrap.dedent(
    (ACTION / "action.yml").read_text().split("      run: |\n", 1)[1]
)


def metadata(name, missing_dependency=False):
    info = {
        "repo_url": f"https://github.com/Test/{name}",
        "name": name, "description": "Fixture", "authors": [],
        "dependencies": ([{"repo_url": "https://github.com/Missing/Dependency",
                           "version": ">=1.0.0"}] if missing_dependency else []),
    }
    return {
        "latest_release_info": info,
        "releases": [{
            "tag": "v1.0.0", "hash": "0" * 128,
            "pak_file_name": f"{name}.pak", "release_date": "2026-01-01T00:00:00",
            "info": info, "release_notes_markdown": "",
            "manifest": {key: [] for key in
                         ("markers", "blueprints", "maps", "replacements", "arbitrary")},
        }],
    }


class RegistryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build through the production integration, including its pinned fetch,
        # patch application and cache key (or reuse that exact patched image).
        with tempfile.TemporaryDirectory(prefix="registry-build-") as directory:
            workspace = Path(directory)
            result, outputs = cls.action(workspace, "validate")
            if result.returncode != 0 or "failed=false" not in outputs:
                raise RuntimeError(result.stdout + outputs)

    @staticmethod
    def action(workspace, command):
        # Docker runs as root; own the writable directories on the host so
        # TemporaryDirectory cleanup also works for unprivileged developers.
        (workspace / "package_db/packages").mkdir(parents=True, exist_ok=True)
        runner = workspace / "runner"
        runner.mkdir(exist_ok=True)
        output = runner / "outputs"
        output.write_text("")
        env = dict(os.environ, COMMAND=command, REPO_URL="", RELEASE_TAG="",
                   GITHUB_TOKEN="fixture-token", LOG_LEVEL="INFO",
                   RUNNER_TEMP=str(runner), GITHUB_WORKSPACE=str(workspace),
                   GITHUB_OUTPUT=str(output), REGISTRY_ACTION_PATH=str(ACTION))
        result = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o",
                                 "pipefail", "-c", ACTION_SHELL], env=env,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return result, output.read_text()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="registry-test-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.db = self.workspace / "package_db"
        (self.db / "packages/Test").mkdir(parents=True)
        self.registry = self.workspace / "registry"
        self.registry.mkdir()
        self.index = self.db / "mod_list_index.txt"
        self.index.write_text("")
        support = self.workspace / "test_support"
        support.mkdir()
        (support / "sitecustomize.py").write_text(textwrap.dedent('''
            import json
            from pathlib import Path
            from zero_infra_mod_registry.models import Mod, Release
            from zero_infra_mod_registry.retriever import GithubModMetadataRetriever

            def fetch_repo(self, repo):
                path = Path("fixtures") / (repo.name + ".json")
                return Mod.from_dict(json.loads(path.read_text())) if path.exists() else None

            def fetch_release(self, mod, tag):
                return Release.from_dict(json.loads(Path("fixtures/release.json").read_text()))

            GithubModMetadataRetriever.fetch_repo_metadata = fetch_repo
            GithubModMetadataRetriever.fetch_release_metadata = fetch_release
        '''))
        (self.workspace / "fixtures").mkdir()

    def write_mod(self, name, missing_dependency=False):
        (self.db / f"packages/Test/{name}.json").write_text(
            json.dumps(metadata(name, missing_dependency)))

    def fixture(self, name, missing_dependency=False):
        (self.workspace / f"fixtures/{name}.json").write_text(
            json.dumps(metadata(name, missing_dependency)))

    def cli(self, *args):
        return subprocess.run([
            "docker", "run", "--rm", "--env", "GITHUB_TOKEN=fixture-token",
            "--env", "LOG_LEVEL=INFO", "--env", "PYTHONPATH=/github/workspace/test_support",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--volume", f"{self.workspace}:/github/workspace",
            "--workdir", "/github/workspace", IMAGE, *args,
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fresh_ingestion_with_empty_terminated_and_unterminated_indexes(self):
        for ending in (None, "", "\n"):
            with self.subTest(ending=ending):
                self.write_mod("Existing")
                self.index.write_text("Test/Existing" + (ending or "") if ending is not None else "")
                org_index = self.registry / "Test.txt"
                org_index.write_text("https://github.com/Test/Existing" + (ending or "")
                                     if ending is not None else "")
                for name in ("NewOne", "NewTwo"):
                    self.fixture(name)
                    self.assert_success(self.cli("add-package", f"https://github.com/Test/{name}"))
                expected = (["Test/Existing"] if ending is not None else []) + ["Test/NewOne", "Test/NewTwo"]
                self.assertEqual(self.index.read_text().splitlines(), expected)
                self.assertEqual(org_index.read_text().splitlines(),
                                 ["https://github.com/" + entry for entry in expected])
                self.assertTrue(self.index.read_bytes().endswith(b"\n"))
                self.assertTrue(org_index.read_bytes().endswith(b"\n"))
                self.assert_success(self.cli("validate"))

    def test_validation_missing_indexed_package_fails_action(self):
        self.index.write_text("Missing/Dependency\n")
        result, outputs = self.action(self.workspace, "validate")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("not found during validation", result.stdout)
        self.assertIn("failed=true", outputs)
        self.assertNotIn("failed=false", outputs)
        self.assertNotIn("Validation complete!", result.stdout)

    def test_validation_missing_release_dependency_fails_action(self):
        self.write_mod("Existing", missing_dependency=True)
        self.index.write_text("Test/Existing\n")
        result, outputs = self.action(self.workspace, "validate")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("requires missing dependency", result.stdout)
        self.assertIn("failed=true", outputs)

    def test_valid_database_passes_action(self):
        self.write_mod("Existing")
        self.index.write_text("Test/Existing")
        result, outputs = self.action(self.workspace, "validate")
        self.assert_success(result)
        self.assertIn("failed=false", outputs)

    def test_invalid_new_package_is_not_written(self):
        self.fixture("Invalid", missing_dependency=True)
        result = self.cli("add-package", "https://github.com/Test/Invalid")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("requires missing dependency", result.stdout)
        self.assertEqual(self.index.read_text(), "")
        self.assertFalse((self.db / "packages/Test/Invalid.json").exists())

    def test_invalid_new_release_is_not_written(self):
        self.write_mod("Existing")
        self.index.write_text("Test/Existing\n")
        release = metadata("Existing", missing_dependency=True)["releases"][0]
        release["tag"] = "v2.0.0"
        (self.workspace / "fixtures/release.json").write_text(json.dumps(release))
        path = self.db / "packages/Test/Existing.json"
        before = path.read_bytes()
        result = self.cli("add-package-release", "https://github.com/Test/Existing", "v2.0.0")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("requires missing dependency", result.stdout)
        self.assertEqual(path.read_bytes(), before)

    def test_processing_failed_retrieval_does_not_write_index(self):
        (self.registry / "Test.txt").write_text("https://github.com/Test/Unavailable")
        result = self.cli("process-registry-updates")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Failures occurred while processing", result.stdout)
        self.assertEqual(self.index.read_text(), "")

    def test_processing_invalid_package_does_not_write_index(self):
        self.fixture("Invalid", missing_dependency=True)
        (self.registry / "Test.txt").write_text("https://github.com/Test/Invalid")
        result = self.cli("process-registry-updates")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("requires missing dependency", result.stdout)
        self.assertEqual(self.index.read_text(), "")

    def test_processing_valid_package_passes_and_can_be_appended(self):
        self.fixture("Existing")
        (self.registry / "Test.txt").write_text("https://github.com/Test/Existing")
        self.assert_success(self.cli("process-registry-updates"))
        self.fixture("New")
        self.assert_success(self.cli("add-package", "https://github.com/Test/New"))
        self.assertEqual(self.index.read_text().splitlines(), ["Test/Existing", "Test/New"])
        self.assert_success(self.cli("validate"))


if __name__ == "__main__":
    unittest.main()
