"""Exercise the upstream Docker CLI and the exact composite action shell.

Only remote metadata retrieval is replaced with deterministic fixtures; registry
loading, validation, processing, index writes, CLI exits and Docker are real.
"""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github/actions/registry"
# Extract rather than copy the production shell, so tests cannot drift from CI.
ACTION_SHELL = textwrap.dedent(
    (ACTION / "action.yml").read_text().split("      run: |\n", 1)[1]
)
REVISION = ACTION_SHELL.split("REVISION=", 1)[1].splitlines()[0].strip()
IMAGE = f"zero-infra-mod-registry:{REVISION}"


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
        # Optional local dependency testing before the upstream SHA is pushed.
        # Production always fetches the pinned commit directly, without patches.
        source = os.environ.get("REGISTRY_TEST_SOURCE")
        if source:
            head = subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip()
            if head != REVISION:
                raise RuntimeError("Local registry test source must match the pinned commit")
            result = subprocess.run(["docker", "build", "--tag", IMAGE, source],
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode != 0:
                raise RuntimeError(result.stdout)
        # Build through the production integration's pinned fetch, or reuse that
        # exact image when testing a not-yet-published dependency locally.
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
                    GITHUB_OUTPUT=str(output))
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
        self._release_sequence = 0
        support = self.workspace / "test_support"
        support.mkdir()
        (support / "sitecustomize.py").write_text(textwrap.dedent('''
            import json
            from pathlib import Path
            from types import SimpleNamespace
            from datetime import datetime
            from github import Github
            import requests
            from zero_infra_mod_registry.models import Release
            from zero_infra_mod_registry.retriever import GithubModMetadataRetriever

            def fetch_release(self, repo, tag):
                path = Path("fixtures/release.json")
                if not path.exists():
                    path = Path("fixtures") / (repo.name + ".json")
                if not path.exists():
                    return None
                data = json.loads(path.read_text())
                entries = data.get("releases", [data])
                return next((Release.from_dict(entry) for entry in entries if entry["tag"] == tag), None)

            GithubModMetadataRetriever.fetch_release_metadata = fetch_release

            def dll_repo(self, name):
                data = json.loads(Path("fixtures/dll-release.json").read_text())
                release = SimpleNamespace(**data)
                release.published_at = datetime.fromisoformat(data["published_at"])
                release.get_assets = lambda: [SimpleNamespace(**asset) for asset in data["assets"]]
                return SimpleNamespace(get_release=lambda tag: release)

            class DllResponse:
                url = "https://example.com/plugin.dll"
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def raise_for_status(self): pass
                def iter_content(self, chunk_size):
                    yield Path("fixtures/plugin.dll").read_bytes()

            Github.get_repo = dll_repo
            def get(url, *args, **kwargs):
                response = DllResponse()
                response.url = url
                response.status_code = 200
                response.text = ""
                if url.endswith("/plugin.json") or url.endswith("/plugin-upload.json"):
                    path = Path("fixtures/plugin-upload.json" if url.endswith("/plugin-upload.json") else "fixtures/plugin.json")
                    response.status_code = 200 if path.exists() else 404
                    response.text = path.read_text() if path.exists() else "missing"
                return response
            requests.get = get
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
            "docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "--env", "GITHUB_TOKEN=fixture-token",
            "--env", "LOG_LEVEL=INFO", "--env", "PYTHONPATH=/github/workspace/test_support",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--volume", f"{self.workspace}:/github/workspace",
            "--workdir", "/github/workspace", IMAGE, *args,
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fresh_ingestion_with_empty_terminated_and_unterminated_indexes(self):
        for sequence, ending in enumerate((None, "", "\n")):
            with self.subTest(ending=ending):
                self.write_mod("Existing")
                self.index.write_text("Test/Existing" + (ending or "") if ending is not None else "")
                org_index = self.registry / "Test.txt"
                org_index.write_text("https://github.com/Test/Existing" + (ending or "")
                                     if ending is not None else "")
                names = (f"NewOne{sequence}", f"NewTwo{sequence}")
                for name in names:
                    self.fixture(name)
                    self.assert_success(self.cli("add-package-release", f"https://github.com/Test/{name}", "v1.0.0"))
                expected = (["Test/Existing"] if ending is not None else []) + [f"Test/{name}" for name in names]
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
        result = self.cli("add-package-release", "https://github.com/Test/Invalid", "v1.0.0")
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

    def test_bulk_commands_are_rejected_without_changes(self):
        for arguments in (("add-package", "https://github.com/Test/Plugin"), ("process-registry-updates",)):
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("invalid choice", result.stdout)
                self.assertEqual(self.index.read_text(), "")

    def test_first_registration_and_update_import_only_requested_tags(self):
        data = metadata("New")
        extra = dict(data["releases"][0], tag="v2.0.0", release_date="2026-02-01T00:00:00")
        data["releases"].append(extra)
        (self.workspace / "fixtures/New.json").write_text(json.dumps(data))
        self.assert_success(self.cli("add-package-release", "https://github.com/Test/New", "v2.0.0"))
        path = self.db / "packages/Test/New.json"
        self.assertEqual([release["tag"] for release in json.loads(path.read_text())["releases"]], ["v2.0.0"])
        self.assert_success(self.cli("add-package-release", "https://github.com/Test/New", "v1.0.0"))
        self.assertEqual([release["tag"] for release in json.loads(path.read_text())["releases"]], ["v2.0.0", "v1.0.0"])
        self.assertEqual(self.index.read_text(), "Test/New\n")
        self.assert_success(self.cli("validate"))

    def dll_fixture(self, version="v1.0.0", assets=1, draft=False, uploaded=False):
        self._release_sequence += 1
        binary = b"DLL fixture bytes"
        (self.workspace / "fixtures/plugin.dll").write_bytes(binary)
        (self.workspace / "fixtures/plugin.json").write_text(json.dumps({
            "name": "Plugin", "description": "Fixture plugin", "authors": ["Author"], "target": "shared", "mod_dependencies": [], "plugin_dependencies": []}))
        release_assets = [{"name": f"Plugin{i}.dll", "browser_download_url": "https://example.com/plugin.dll",
                           "size": len(binary)} for i in range(assets)]
        if uploaded:
            (self.workspace / "fixtures/plugin-upload.json").write_text((self.workspace / "fixtures/plugin.json").read_text())
            release_assets.append({"name": "plugin.json", "browser_download_url": "https://example.com/plugin-upload.json", "size": 100})
        (self.workspace / "fixtures/dll-release.json").write_text(json.dumps({
            "tag_name": version, "draft": draft, "body": "# Release notes\n\nPlugin changes.",
            "published_at": (datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self._release_sequence)).isoformat(),
            "assets": release_assets}))

    @property
    def plugin_path(self):
        return self.workspace / "dll_db/packages/Test/Plugin.json"

    def dll_entries(self):
        package = json.loads(self.plugin_path.read_text())
        return [{"organization": "Test", "name": "Plugin", "version": release["tag"].removeprefix("v"),
                 "download_url": release["download_url"], "sha256": release["hash"], "size": release["size"], "info": release["info"]}
                for release in package["releases"]]

    def test_dll_registration_separate_index_and_duplicate_rejected(self):
        self.dll_fixture()
        args = ("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0")
        self.assert_success(self.cli(*args))
        path = self.plugin_path
        entries = self.dll_entries()
        self.assertEqual(entries[0], {
            "organization": "Test", "name": "Plugin", "version": "1.0.0",
            "download_url": "https://example.com/plugin.dll",
            "size": len(b"DLL fixture bytes"), "sha256": hashlib.sha256(b"DLL fixture bytes").hexdigest(),
            "info": {"name": "Plugin", "description": "Fixture plugin", "authors": ["Author"], "target": "shared", "mod_dependencies": [], "plugin_dependencies": [], "repo_url": "https://github.com/Test/Plugin"}})
        package = json.loads(path.read_text())
        self.assertEqual(package["latest_release_info"], entries[0]["info"])
        self.assertEqual(package["releases"][0]["release_notes_markdown"], "# Release notes\n\nPlugin changes.")
        self.assertNotIn("manifest", package["releases"][0])
        self.assertEqual((self.workspace / "dll_db/plugin_list_index.txt").read_text(), "Test/Plugin\n")
        self.assertEqual(self.index.read_text(), "")
        self.assertFalse((self.registry / "Test.txt").exists())
        self.assert_success(self.cli("validate", "--verify-dll-downloads"))
        before = path.read_bytes()
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_dll_invalid_releases_do_not_write_index(self):
        for kwargs in ({"assets": 0}, {"assets": 2}, {"version": "latest"}, {"draft": True}):
            with self.subTest(kwargs=kwargs):
                self.dll_fixture(**kwargs)
                self.assertNotEqual(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0").returncode, 0)
                self.assertFalse(self.plugin_path.exists())

    def test_dll_dry_run_does_not_write_index(self):
        self.dll_fixture()
        self.assert_success(self.cli("--dry-run", "add-dll-release", "https://github.com/Test/Plugin", "v1.0.0"))
        self.assertFalse(self.plugin_path.exists())

    def test_dll_multiple_assets_require_exact_selection(self):
        self.dll_fixture(assets=2)
        common = ("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0")
        for filename in ("Missing.dll", "plugin0.dll", "*.dll", "Plugin0.pak"):
            with self.subTest(filename=filename):
                self.assertNotEqual(self.cli(*common, "--dll-file", filename).returncode, 0)
                self.assertFalse(self.plugin_path.exists())
        self.assert_success(self.cli("--dry-run", *common, "--dll-file", "Plugin1.dll"))
        self.assertFalse(self.plugin_path.exists())
        self.assert_success(self.cli(*common, "--dll-file", "Plugin1.dll"))
        entries = self.dll_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["sha256"], hashlib.sha256(b"DLL fixture bytes").hexdigest())

    def test_dll_missing_plugin_json_and_dependencies_do_not_write_index(self):
        self.dll_fixture()
        path = self.workspace / "fixtures/plugin.json"
        path.unlink()
        common = ("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0")
        self.assertNotEqual(self.cli(*common).returncode, 0)
        self.assertFalse(self.plugin_path.exists())
        info = {"name": "Plugin", "description": "Description", "authors": ["Author"],
                "plugin_dependencies": [{"repo_url": "https://github.com/Test/Missing", "version": "1.0.0"}], "mod_dependencies": []}
        path.write_text(json.dumps(info))
        self.assertNotEqual(self.cli(*common).returncode, 0)
        self.assertFalse(self.plugin_path.exists())

    def test_plugin_icon_and_images_are_preserved(self):
        self.dll_fixture()
        path = self.workspace / "fixtures/plugin.json"
        info = json.loads(path.read_text())
        info.update(icon_url="https://example.com/icon.png", image_urls=["https://example.com/screenshot.png"])
        path.write_text(json.dumps(info))
        self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0"))
        entries = self.dll_entries()
        self.assertEqual(entries[0]["info"], dict(info, repo_url="https://github.com/Test/Plugin"))

    def test_uploaded_plugin_metadata_takes_precedence(self):
        self.dll_fixture(uploaded=True)
        path = self.workspace / "fixtures/plugin-upload.json"
        info = json.loads(path.read_text())
        info.update(name="Uploaded plugin", description="Corrected description", target="server")
        path.write_text(json.dumps(info))
        self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0"))
        self.assertEqual(self.dll_entries()[0]["info"], dict(info, repo_url="https://github.com/Test/Plugin"))
        self.assert_success(self.cli("validate", "--verify-dll-downloads"))

    def test_invalid_uploaded_metadata_does_not_fall_back_or_write(self):
        self.dll_fixture(uploaded=True)
        (self.workspace / "fixtures/plugin-upload.json").write_text("{}")
        self.assertNotEqual(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0").returncode, 0)
        self.assertFalse(self.plugin_path.exists())

    def test_plugin_target_values_and_legacy_default(self):
        for i, target in enumerate(("server", "client", "shared", None), start=1):
            with self.subTest(target=target):
                tag = f"v{i}.0.0"
                self.dll_fixture(version=tag)
                path = self.workspace / "fixtures/plugin.json"
                info = json.loads(path.read_text())
                if target is None:
                    del info["target"]
                else:
                    info["target"] = target
                path.write_text(json.dumps(info))
                self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", tag))
                self.assertEqual(self.dll_entries()[0]["info"]["target"], target or "shared")

    def test_mod_and_plugin_dependencies_use_separate_indexes(self):
        self.dll_fixture()
        self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0"))
        pak = metadata("Pak")
        for info in [pak["latest_release_info"], pak["releases"][0]["info"]]:
            info["mod_dependencies"] = []
            info["plugin_dependencies"] = [{"repo_url": "https://github.com/Test/Plugin", "version": "1.0.0"}]
        (self.workspace / "fixtures/Pak.json").write_text(json.dumps(pak))
        self.assert_success(self.cli("add-package-release", "https://github.com/Test/Pak", "v1.0.0"))
        self.dll_fixture(version="v2.0.0")
        info = {"name": "Plugin", "description": "Description", "authors": ["Author"],
                "mod_dependencies": [{"repo_url": "https://github.com/Test/Pak", "version": "1.0.0"}],
                "plugin_dependencies": []}
        (self.workspace / "fixtures/plugin.json").write_text(json.dumps(info))
        self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v2.0.0"))
        self.assert_success(self.cli("validate", "--verify-dll-downloads"))
        # The DLL registry contains Test/Plugin, but the pak registry does not.
        self.dll_fixture(version="v3.0.0")
        info["mod_dependencies"] = [{"repo_url": "https://github.com/Test/Plugin", "version": "1.0.0"}]
        (self.workspace / "fixtures/plugin.json").write_text(json.dumps(info))
        self.assertNotEqual(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v3.0.0").returncode, 0)

    def test_dll_prerelease_dry_run_and_version_preservation(self):
        for tag in ("v1.0.0-RC2", "v1.0.0-RC1", "v1.0.0-rc0"):
            with self.subTest(tag=tag):
                self.dll_fixture(version=tag)
                before = self.plugin_path.read_bytes() if self.plugin_path.exists() else None
                self.assert_success(self.cli("--dry-run", "add-dll-release", "https://github.com/Test/Plugin", tag))
                after = self.plugin_path.read_bytes() if self.plugin_path.exists() else None
                self.assertEqual(after, before)
                self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", tag))
                entries = self.dll_entries()
                self.assertEqual(entries[0]["version"], tag.removeprefix("v"))

    def test_dll_corrupt_metadata_and_download_fail_validation(self):
        self.dll_fixture()
        self.assert_success(self.cli("add-dll-release", "https://github.com/Test/Plugin", "v1.0.0"))
        (self.workspace / "fixtures/plugin.dll").write_bytes(b"tampered")
        self.assertNotEqual(self.cli("validate", "--verify-dll-downloads").returncode, 0)
        path = self.plugin_path
        package = json.loads(path.read_text())
        for field, value in (("tag", "latest"), ("hash", "bad"),
                             ("size", 0), ("size", True), ("download_url", "http://example.com/a.dll")):
            with self.subTest(field=field):
                invalid = dict(package, releases=[dict(package["releases"][0], **{field: value})])
                path.write_text(json.dumps(invalid))
                self.assertNotEqual(self.cli("validate").returncode, 0)


if __name__ == "__main__":
    unittest.main()
