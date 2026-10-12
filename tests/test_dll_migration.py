"""Check the imported release data without depending on live GitHub responses."""
from datetime import datetime
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATED_TAGS = {"v1.0.0-RC2", "v1.0.0-RC1", "v0.5.0"}


class DllMigrationTests(unittest.TestCase):
    def setUp(self):
        self.package = json.loads((ROOT / "dll_db/packages/Chiv2-Community/UnchainedPlugin.json").read_text())
        self.releases = self.package["releases"]

    def test_migrated_releases_are_in_the_new_package(self):
        self.assertIn("Chiv2-Community/UnchainedPlugin", (ROOT / "dll_db/plugin_list_index.txt").read_text().splitlines())
        self.assertFalse((ROOT / "dll_db/index.json").exists())
        tags = {release["tag"] for release in self.releases}
        self.assertEqual(MIGRATED_TAGS, tags)
        self.assertNotIn("v0.0.1dev", tags)
        self.assertEqual(len(self.releases), len(tags))
        dates = [datetime.fromisoformat(release["release_date"]) for release in self.releases]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(self.package["latest_release_info"], self.releases[0]["info"])

    def test_imported_metadata_and_asset_selection(self):
        expected_info = {
            "name": "Unchained Core Plugin",
            "description": "Allows users to run mods and connect to unchained servers. Required for modded play and self-hosted servers.",
            "authors": ["Dr Long", "Jacoby6000", "Nihilianth", "Reciate"],
            "target": "shared", "mod_dependencies": [], "plugin_dependencies": [],
            "repo_url": "https://github.com/Chiv2-Community/UnchainedPlugin",
        }
        for release in self.releases:
            if release["tag"] not in MIGRATED_TAGS:
                continue
            with self.subTest(tag=release["tag"]):
                self.assertEqual(release["info"], expected_info)
                self.assertEqual(release["dll_file_name"], "UnchainedPlugin.dll")
                self.assertEqual(release["download_url"], f"https://github.com/Chiv2-Community/UnchainedPlugin/releases/download/{release['tag']}/UnchainedPlugin.dll")
                self.assertRegex(release["hash"], r"^[a-f0-9]{64}$")
                self.assertGreater(release["size"], 0)
                self.assertIsInstance(release["release_notes_markdown"], str)
                self.assertNotIn("manifest", release)

    def test_previously_approved_hashes_and_sizes_are_preserved(self):
        approved = {
            "v0.5.0": ("b2e852828ed0b67ae1d37bcb34c1558456b84c67653b139bae097b629b23cfea", 3646464),
            "v1.0.0-RC1": ("b91b30d8fff02f2e3da51c97bb3d00fd47c3487f1a92ef3dc3c64160723c9cde", 23660032),
            "v1.0.0-RC2": ("fb8a576e48c910f340c9822210d0230eb458ae1d2b8a8800fd509422ae9d9e69", 23812608),
        }
        by_tag = {release["tag"]: release for release in self.releases}
        for tag, fingerprint in approved.items():
            with self.subTest(tag=tag):
                self.assertEqual((by_tag[tag]["hash"], by_tag[tag]["size"]), fingerprint)
