import importlib.util
import pathlib
import sys
import tempfile
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "model_manifest.py"
spec = importlib.util.spec_from_file_location("model_manifest", path)
mm = importlib.util.module_from_spec(spec)
sys.modules["model_manifest"] = mm
spec.loader.exec_module(mm)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "model.safetensors").write_bytes(b"weights-v1")
        (self.root / "config.json").write_text("{}")
        self.manifest = mm.create(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_directory_verifies(self):
        self.assertEqual(mm.verify(self.root, self.manifest), [])

    def test_tampered_weights_detected(self):
        (self.root / "model.safetensors").write_bytes(b"weights-v1-backdoor")
        self.assertEqual(mm.verify(self.root, self.manifest), ["modified: model.safetensors"])

    def test_added_and_removed_files_detected(self):
        (self.root / "config.json").unlink()
        (self.root / "extra.py").write_text("print('x')")
        self.assertEqual(mm.verify(self.root, self.manifest), ["missing: config.json", "unexpected: extra.py"])

    def test_pickle_formats_refused(self):
        (self.root / "weights.pkl").write_bytes(b"x")
        with self.assertRaises(ValueError):
            mm.create(self.root)

    def test_cli_round_trip(self):
        self.assertEqual(mm.main(["create", str(self.root)]), 0)
        self.assertEqual(mm.main(["verify", str(self.root)]), 0)
        (self.root / "config.json").write_text('{"tampered": true}')
        self.assertEqual(mm.main(["verify", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
