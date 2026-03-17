"""Tests for halctl fleet provisioning and isolation."""

import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml


def _write_fleet_config(tmp: str, source: str) -> str:
    """Write a minimal fleet-config.yaml and return its path."""
    config = {
        "base": {
            "source": source,
            "exclude": [
                "memory/",
                ".env*",
                "nanoclaw.db",
                "groups/",
                "queue/",
            ],
            "lock": ["CLAUDE.md", "src/"],
            "open": ["workspace/", "projects/", "groups/", "memory/"],
        },
        "profiles": {
            "default": {
                "personality": "default",
                "services": [],
                "telegram_bot_name": None,
            },
            "testuser": {
                "personality": "discovering-ben",
                "services": ["gh", "vercel"],
                "telegram_bot_name": "HALTest_bot",
            },
        },
    }
    config_path = os.path.join(tmp, "fleet-config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    return config_path


def _create_mock_source(tmp: str) -> str:
    """Create a mock prime nanoclaw source tree."""
    source = os.path.join(tmp, "nanoclaw")
    os.makedirs(source)

    # Governance files (should be locked after provision)
    Path(source, "CLAUDE.md").write_text("# Prime CLAUDE.md\n")
    os.makedirs(os.path.join(source, "src"))
    Path(source, "src", "index.ts").write_text("// main\n")

    # Files that should be excluded
    os.makedirs(os.path.join(source, "memory", "notes"), exist_ok=True)
    Path(source, "memory", "INDEX.md").write_text("# Memory\n")
    Path(source, ".env").write_text("SECRET=bad\n")
    Path(source, "nanoclaw.db").write_text("fake-db\n")
    os.makedirs(os.path.join(source, "groups", "telegram_main"), exist_ok=True)
    Path(source, "groups", "telegram_main", "chat.txt").write_text("msg\n")
    os.makedirs(os.path.join(source, "queue"), exist_ok=True)
    Path(source, "queue", "job.yaml").write_text("job\n")

    # Regular files (should be copied)
    Path(source, "package.json").write_text('{"name": "nanoclaw"}\n')
    os.makedirs(os.path.join(source, "container"))
    Path(source, "container", "Dockerfile").write_text("FROM node\n")

    return source


def _unlock_tree(path: str) -> None:
    """Recursively unlock a directory tree for cleanup."""
    for root, dirs, files in os.walk(path):
        try:
            os.chmod(root, stat.S_IRWXU)
        except OSError:
            pass
        for f in files:
            try:
                os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass


class BaseHalctlTest(unittest.TestCase):
    """Base class with common setup/teardown for halctl tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source = _create_mock_source(self.tmp)
        self.config_path = _write_fleet_config(self.tmp, self.source)
        self.fleet_base = Path(self.tmp) / "halfleet"

    def tearDown(self):
        _unlock_tree(self.tmp)
        shutil.rmtree(self.tmp)

    def _provision(self, name="testinst", personality=None):
        from halos.halctl.provision import create_instance
        return create_instance(
            name=name,
            personality=personality,
            config_path=Path(self.config_path),
            fleet_base=self.fleet_base,
        )

    def _load_manifest(self):
        manifest_path = self.fleet_base / "FLEET.yaml"
        with open(manifest_path) as f:
            return yaml.safe_load(f)


class TestExcludedFiles(BaseHalctlTest):
    """Verify excluded files are not present in provisioned deployment."""

    def test_excluded_memory_not_present(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        memory_index = deploy / "memory" / "INDEX.md"
        self.assertFalse(memory_index.exists(), "prime memory INDEX.md must not be copied")

    def test_excluded_env_files_not_present(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        self.assertFalse((deploy / ".env").exists(), ".env must not be copied")

    def test_excluded_database_not_present(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        self.assertFalse((deploy / "nanoclaw.db").exists(), "nanoclaw.db must not be copied")

    def test_excluded_groups_not_copied(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        chat = deploy / "groups" / "telegram_main" / "chat.txt"
        self.assertFalse(chat.exists(), "prime groups content must not be copied")

    def test_excluded_queue_not_present(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        self.assertFalse((deploy / "queue").exists(), "queue must not be copied")

    def test_regular_files_are_present(self):
        entry = self._provision()
        deploy = Path(entry["path"])
        self.assertTrue((deploy / "package.json").exists(), "package.json should be copied")


class TestLockedPermissions(BaseHalctlTest):
    """Verify locked files have correct read-only permissions."""

    def test_claude_md_is_read_only(self):
        entry = self._provision("locktest")
        deploy = Path(entry["path"])
        claude_md = deploy / "CLAUDE.md"
        mode = oct(claude_md.stat().st_mode)[-3:]
        self.assertEqual(mode, "444", f"CLAUDE.md should be 444, got {mode}")

    def test_locked_dir_files_are_read_only(self):
        entry = self._provision("locktest2")
        deploy = Path(entry["path"])
        index_ts = deploy / "src" / "index.ts"
        mode = oct(index_ts.stat().st_mode)[-3:]
        self.assertEqual(mode, "444", f"src/index.ts should be 444, got {mode}")

    def test_locked_dir_has_execute_permission(self):
        entry = self._provision("locktest3")
        deploy = Path(entry["path"])
        src_dir = deploy / "src"
        mode = oct(src_dir.stat().st_mode)[-3:]
        self.assertEqual(mode, "555", f"src/ dir should be 555, got {mode}")

    def test_locked_file_not_writable(self):
        entry = self._provision("locktest4")
        deploy = Path(entry["path"])
        claude_md = deploy / "CLAUDE.md"
        st = claude_md.stat()
        writable = bool(st.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        self.assertFalse(writable, "CLAUDE.md must not have any write bits set")


class TestFleetManifest(BaseHalctlTest):
    """Verify FLEET.yaml is correctly updated on create."""

    def test_create_adds_instance_to_manifest(self):
        self._provision("alice")
        data = self._load_manifest()
        names = [i["name"] for i in data["instances"]]
        self.assertIn("alice", names)

    def test_manifest_entry_has_required_fields(self):
        self._provision("bob")
        data = self._load_manifest()
        entry = data["instances"][0]
        for field in ("name", "path", "telegram_bot_token_env", "personality",
                      "services", "created", "status"):
            self.assertIn(field, entry, f"Missing field: {field}")

    def test_manifest_status_is_active_on_create(self):
        self._provision("charlie")
        data = self._load_manifest()
        entry = data["instances"][0]
        self.assertEqual(entry["status"], "active")

    def test_multiple_creates_append_to_manifest(self):
        self._provision("dave")
        self._provision("eve")
        data = self._load_manifest()
        self.assertEqual(len(data["instances"]), 2)
        names = [i["name"] for i in data["instances"]]
        self.assertIn("dave", names)
        self.assertIn("eve", names)

    def test_duplicate_name_raises_error(self):
        self._provision("frank")
        with self.assertRaises(FileExistsError):
            self._provision("frank")

    def test_personality_from_profile(self):
        self._provision("testuser")
        data = self._load_manifest()
        entry = [i for i in data["instances"] if i["name"] == "testuser"][0]
        self.assertEqual(entry["personality"], "discovering-ben")

    def test_personality_override(self):
        self._provision("testuser2", personality="custom")
        data = self._load_manifest()
        entry = [i for i in data["instances"] if i["name"] == "testuser2"][0]
        self.assertEqual(entry["personality"], "custom")


class TestFreezeFoldFry(BaseHalctlTest):
    """Verify freeze/fold/fry update the fleet manifest correctly."""

    def test_freeze_sets_status_frozen(self):
        self._provision("freezeme")
        from halos.halctl.provision import freeze_instance
        freeze_instance("freezeme", fleet_base=self.fleet_base)
        data = self._load_manifest()
        entry = [i for i in data["instances"] if i["name"] == "freezeme"][0]
        self.assertEqual(entry["status"], "frozen")

    def test_fold_sets_status_folded(self):
        self._provision("foldme")
        from halos.halctl.provision import fold_instance
        fold_instance("foldme", fleet_base=self.fleet_base)
        data = self._load_manifest()
        entry = [i for i in data["instances"] if i["name"] == "foldme"][0]
        self.assertEqual(entry["status"], "folded")

    def test_fry_sets_status_fried(self):
        self._provision("fryme")
        from halos.halctl.provision import fry_instance
        fry_instance("fryme", confirm=True, fleet_base=self.fleet_base)
        data = self._load_manifest()
        entry = [i for i in data["instances"] if i["name"] == "fryme"][0]
        self.assertEqual(entry["status"], "fried")

    def test_fry_without_confirm_raises(self):
        self._provision("safeme")
        from halos.halctl.provision import fry_instance
        with self.assertRaises(ValueError):
            fry_instance("safeme", confirm=False, fleet_base=self.fleet_base)

    def test_fry_deletes_deployment(self):
        entry = self._provision("wipeme")
        deploy = Path(entry["path"])
        self.assertTrue(deploy.exists())
        from halos.halctl.provision import fry_instance
        fry_instance("wipeme", confirm=True, fleet_base=self.fleet_base)
        self.assertFalse(deploy.exists(), "fry should delete the deployment directory")

    def test_freeze_nonexistent_raises(self):
        from halos.halctl.provision import freeze_instance
        with self.assertRaises(ValueError):
            freeze_instance("ghost", fleet_base=self.fleet_base)


class TestOpenDirs(BaseHalctlTest):
    """Verify open directories are created."""

    def test_open_dirs_exist(self):
        entry = self._provision("opentest")
        deploy = Path(entry["path"])
        for d in ["workspace", "projects", "groups", "memory"]:
            self.assertTrue((deploy / d).exists(), f"open dir {d}/ should exist")
            self.assertTrue((deploy / d).is_dir(), f"{d} should be a directory")


class TestEcosystemConfig(BaseHalctlTest):
    """Verify pm2 ecosystem config is generated."""

    def test_ecosystem_config_generated(self):
        entry = self._provision("ecotest")
        eco = self.fleet_base / "microhal-ecotest" / "ecosystem.config.js"
        self.assertTrue(eco.exists(), "ecosystem.config.js should be generated")
        content = eco.read_text()
        self.assertIn("microhal-ecotest", content)
        self.assertIn("MICROHAL_ECOTEST_BOT_TOKEN", content)


class TestTemplateComposition(BaseHalctlTest):
    """Verify CLAUDE.md is composed from template layers."""

    def test_claude_md_contains_base_content(self):
        entry = self._provision("tmpltest", personality="default")
        deploy = Path(entry["path"])
        claude_md = deploy / "CLAUDE.md"
        os.chmod(claude_md, stat.S_IRUSR | stat.S_IWUSR)
        content = claude_md.read_text()
        self.assertIn("microHAL", content)

    def test_claude_md_replaces_prime_content(self):
        entry = self._provision("tmpltest2", personality="default")
        deploy = Path(entry["path"])
        claude_md = deploy / "CLAUDE.md"
        os.chmod(claude_md, stat.S_IRUSR | stat.S_IWUSR)
        content = claude_md.read_text()
        self.assertNotIn("Prime CLAUDE.md", content)


if __name__ == "__main__":
    unittest.main()
