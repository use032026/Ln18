"""Safety contracts for the production resource exporter; no source repo writes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("catalog_sync", PACKAGE / "tools/sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncContractTest(unittest.TestCase):
    def setUp(self):
        parent = PACKAGE.parent.parent / ".codex-build/sync-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temporary.name)
        self.package = self.root / "package"
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        (self.package / "renderers").mkdir(parents=True)
        (self.package / "catalog/pc").mkdir(parents=True)
        (self.package / "catalog/index.json").write_text('{"packageVersion":"0.2.0"}')
        (self.package / "pubspec.yaml").write_text("version: 0.2.0\n")
        self.renderer = self.package / "renderers/pc.py"
        self.renderer.write_text("def render(package_root, consumer_root, config):\n    return {'src/messages.ts': 'export const message = \\\"Original\\\";\\n'}\n")
        self.config = {"schemaVersion": 1, "catalogVersion": "0.2.0", "renderer": "pc"}

    def tearDown(self):
        self.temporary.cleanup()

    def run_sync(self, *args):
        (self.consumer / "l10n.resources.json").write_text(json.dumps(self.config))
        with patch.object(sync, "PACKAGE", self.package), patch.object(sys, "argv", ["sync.py", "--consumer-root", str(self.consumer), *args]):
            sync.main()

    def test_export_check_and_detect_unmanaged_change_without_rewriting(self):
        self.run_sync()
        self.run_sync("--check")
        output = self.consumer / "src/messages.ts"
        output.write_text("hand edit")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.run_sync("--check")
        self.assertEqual(output.read_text(), "hand edit")

    def test_check_never_bootstraps_missing_dependencies(self):
        self.config["flutterBundle"] = "l10n.bundle.json"
        (self.consumer / "l10n.bundle.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "read-only"), patch.object(sync.subprocess, "run") as run:
            self.run_sync("--check")
        run.assert_not_called()
        self.assertFalse((self.package / ".dart_tool").exists())
        self.assertFalse((self.consumer / "src").exists())

    def test_version_drift_is_rejected_before_writing(self):
        self.config["catalogVersion"] = "0.1.0"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            self.run_sync()
        self.assertFalse((self.consumer / "src").exists())

    def test_unsafe_output_and_symlink_are_rejected(self):
        self.renderer.write_text("def render(*args):\n    return {'../outside.txt': 'text'}\n")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.run_sync()
        self.renderer.write_text("def render(*args):\n    return {'link/messages.ts': 'text'}\n")
        (self.consumer / "link").symlink_to(self.package, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_sync()

    def test_removed_output_requires_explicit_migration(self):
        self.run_sync()
        self.renderer.write_text("def render(*args):\n    return {'src/renamed.ts': 'new'}\n")
        with self.assertRaisesRegex(ValueError, "paths changed"):
            self.run_sync()
        self.assertTrue((self.consumer / "src/messages.ts").is_file())


if __name__ == "__main__":
    unittest.main()
