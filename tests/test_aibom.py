import importlib.util
import pathlib
import sys
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "generate_aibom.py"
spec = importlib.util.spec_from_file_location("generate_aibom", path)
aibom = importlib.util.module_from_spec(spec)
sys.modules["generate_aibom"] = aibom
spec.loader.exec_module(aibom)

GOOD = {"id": "m", "name": "M", "version": "1", "source": "huggingface.co/org/model",
        "license": "Apache-2.0", "serialization": "safetensors", "sha256": "a" * 64}


class ValidationTests(unittest.TestCase):
    def test_valid_entry(self):
        self.assertEqual(aibom.validate(GOOD), [])

    def test_unpinned_external_model_rejected(self):
        bad = {**GOOD, "sha256": "latest"}
        self.assertTrue(any("sha256" in p for p in aibom.validate(bad)))

    def test_untrusted_source_rejected(self):
        bad = {**GOOD, "source": "downloads.example/model.bin"}
        self.assertTrue(any("trusted" in p for p in aibom.validate(bad)))

    def test_pickle_serialization_rejected(self):
        bad = {**GOOD, "serialization": "pickle"}
        self.assertTrue(any("unsafe serialization" in p for p in aibom.validate(bad)))

    def test_missing_license_rejected(self):
        bad = {k: v for k, v in GOOD.items() if k != "license"}
        self.assertTrue(any("license" in p for p in aibom.validate(bad)))


class BomTests(unittest.TestCase):
    def test_cyclonedx_shape(self):
        bom = aibom.build_bom([GOOD])
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        component = bom["components"][0]
        self.assertEqual(component["type"], "machine-learning-model")
        self.assertEqual(component["hashes"][0]["content"], "a" * 64)

    def test_first_party_model_is_hashed_from_repo(self):
        entry = {**GOOD, "source": "first-party", "path": "apps/llm_gateway/guard.py"}
        entry.pop("sha256")
        digest = aibom.build_bom([entry])["components"][0]["hashes"][0]["content"]
        self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
