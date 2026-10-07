import importlib.util
import pathlib
import sys
import unittest

SPEC = importlib.util.spec_from_file_location(
    "check_secrets", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_secrets.py"
)
cs = importlib.util.module_from_spec(SPEC)
sys.modules["check_secrets"] = cs
SPEC.loader.exec_module(cs)

# Fake tokens are assembled at runtime so this file never contains a real-looking secret.
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
FAKE_ANTHROPIC = "sk-ant-" + "api03-abcdefghijklmnopqrstuvwxyz0123"
FAKE_KEY_BLOCK = "-----BEGIN " + "RSA PRIVATE KEY-----"


class ScanLineTests(unittest.TestCase):
    def test_detects_known_token_formats(self):
        for label, value in [
            ("aws-access-key-id", FAKE_AWS),
            ("github-token", FAKE_GH),
            ("anthropic-api-key", FAKE_ANTHROPIC),
            ("private-key-block", FAKE_KEY_BLOCK),
        ]:
            with self.subTest(label=label):
                self.assertIn(label, cs.scan_line(f"value = {value}"))

    def test_detects_hardcoded_credential_assignment(self):
        line = 'db_password = "hunter2hunter2hunter2"'  # secret-scan:allow
        self.assertIn("hardcoded-credential", cs.scan_line(line))

    def test_ignores_placeholders_and_references(self):
        for line in [
            'api_key = "your-api-key-goes-here"',
            'token: "${GITHUB_TOKEN}"',
            'password = "<set-in-secret-manager>"',
            "token: ${{ secrets.GITHUB_TOKEN }}",
        ]:
            with self.subTest(line=line):
                self.assertEqual(cs.scan_line(line), [])

    def test_allow_marker_suppresses_finding(self):
        self.assertEqual(cs.scan_line(f"x = {FAKE_AWS}  # secret-scan:allow"), [])


class FilenameTests(unittest.TestCase):
    def test_forbidden_names(self):
        for name in [".env", ".env.production", "deploy/tls.key", "ca.pem", "terraform.tfstate", "kubeconfig"]:
            with self.subTest(name=name):
                self.assertTrue(cs.forbidden_name(name))

    def test_allowed_names(self):
        for name in [".env.example", "README.md", "app/main.py"]:
            with self.subTest(name=name):
                self.assertFalse(cs.forbidden_name(name))


class DiffParsingTests(unittest.TestCase):
    def test_only_added_lines_are_scanned(self):
        diff = f"+++ b/app.py\n-old = {FAKE_AWS}\n+new = {FAKE_GH}\n"
        findings = cs.scan_added(diff)
        self.assertEqual([f.rule for f in findings], ["github-token"])
        self.assertEqual(findings[0].where, "app.py")

    def test_rendered_finding_never_prints_full_secret(self):
        rendered = cs.Finding("github-token", "a.py", "x = " + FAKE_GH).render()
        self.assertNotIn(FAKE_GH, rendered)


if __name__ == "__main__":
    unittest.main()
