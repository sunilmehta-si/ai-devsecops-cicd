import importlib.util
import json
import pathlib
import sys
import unittest

from apps.agent_tools.policy import ToolPolicy

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run_ai_security.py"
spec = importlib.util.spec_from_file_location("run_ai_security", path)
runner = importlib.util.module_from_spec(spec)
sys.modules["run_ai_security"] = runner
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def cases(self):
        return json.loads(runner.CORPUS.read_text())["cases"]

    def test_every_case_passes_with_default_policy(self):
        policy = ToolPolicy()
        for case in self.cases():
            with self.subTest(case=case["id"]):
                self.assertEqual(runner.run_case(case, policy)[0], case["expect"])

    def test_weakened_policy_is_detected(self):
        """Negative control: if egress is opened up, the corpus must notice."""
        weak = ToolPolicy(allowed_hosts=frozenset({"api.github.com", "attacker.example"}))
        exfil = next(c for c in self.cases() if c["id"] == "INJ-003")
        self.assertNotEqual(runner.run_case(exfil, weak)[0], exfil["expect"])

    def test_corpus_has_unique_ids_and_benign_controls(self):
        ids = [c["id"] for c in self.cases()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(c["expect"] == "allow" for c in self.cases()))


if __name__ == "__main__":
    unittest.main()
