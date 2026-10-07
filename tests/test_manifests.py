import copy
import importlib.util
import pathlib
import sys
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_manifests", ROOT / "scripts" / "validate_manifests.py")
vm = importlib.util.module_from_spec(spec)
sys.modules["validate_manifests"] = vm
spec.loader.exec_module(vm)

GOOD = yaml.safe_load((ROOT / "deploy" / "base" / "deployment.yaml").read_text())


def mutate(fn):
    doc = copy.deepcopy(GOOD)
    fn(doc["spec"]["template"]["spec"])
    return vm.check_workload(doc)


class ManifestTests(unittest.TestCase):
    def test_shipped_deployment_is_compliant(self):
        self.assertEqual(vm.check_workload(GOOD), [])

    def test_each_violation_is_caught(self):
        cases = {
            "privileged": lambda s: s["containers"][0]["securityContext"].update(privileged=True),
            "latest tag": lambda s: s["containers"][0].update(image="ghcr.io/sunilmehta-si/app:latest"),
            "untagged": lambda s: s["containers"][0].update(image="ghcr.io/sunilmehta-si/app"),
            "foreign registry": lambda s: s["containers"][0].update(image="docker.io/library/nginx:1.27"),
            "writable root": lambda s: s["containers"][0]["securityContext"].update(readOnlyRootFilesystem=False),
            "no limits": lambda s: s["containers"][0].pop("resources"),
            "no cpu limit": lambda s: s["containers"][0]["resources"]["limits"].pop("cpu"),
            "keeps capabilities": lambda s: s["containers"][0]["securityContext"].pop("capabilities"),
            "runs as root": lambda s: s["securityContext"].update(runAsNonRoot=False),
            "host network": lambda s: s.update(hostNetwork=True),
        }
        for label, fn in cases.items():
            with self.subTest(label=label):
                self.assertTrue(mutate(fn), f"{label} should be rejected")

    def test_empty_directory_fails_closed(self):
        self.assertEqual(vm.main(["/nonexistent-dir"]), 1)

    def test_shipped_manifests_pass_cli(self):
        self.assertEqual(vm.main([]), 0)


if __name__ == "__main__":
    unittest.main()
