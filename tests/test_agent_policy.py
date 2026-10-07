import unittest

from apps.agent_tools.dispatcher import dispatch
from apps.agent_tools.policy import PolicyDenied, ToolPolicy

POLICY = ToolPolicy()


class PolicyTests(unittest.TestCase):
    def test_unknown_tool_denied(self):
        self.assertFalse(dispatch({"tool": "run_shell", "args": {"cmd": "id"}}, POLICY)["ok"])

    def test_write_needs_approval(self):
        call = {"tool": "write_file", "args": {"path": "notes.txt"}}
        self.assertFalse(dispatch(call, POLICY)["ok"])
        self.assertTrue(dispatch(call, POLICY, approved=True)["ok"])

    def test_path_traversal_blocked(self):
        for path in ["../etc/passwd", "/etc/shadow", "a/../../root/.ssh", "docs/../../../x"]:
            with self.subTest(path=path), self.assertRaises(PolicyDenied):
                POLICY.resolve_path(path)

    def test_protected_files_blocked(self):
        for path in [".env", "app/.env.production", ".git/config", ".aws/credentials", "x/id_rsa"]:
            with self.subTest(path=path), self.assertRaises(PolicyDenied):
                POLICY.resolve_path(path)

    def test_normal_paths_allowed(self):
        self.assertEqual(POLICY.resolve_path("docs/readme.md"), "/workspace/docs/readme.md")
        self.assertEqual(POLICY.resolve_path("docs/../src/a.py"), "/workspace/src/a.py")

    def test_url_rules(self):
        for url in ["http://api.github.com/x", "https://evil.example/x", "https://user:pw@api.github.com/x",
                    "file:///etc/passwd", "https://169.254.169.254/latest/meta-data"]:
            with self.subTest(url=url), self.assertRaises(PolicyDenied):
                POLICY.check_url(url)
        POLICY.check_url("https://api.github.com/repos/x/y")

    def test_malformed_calls(self):
        self.assertFalse(dispatch({"tool": 5}, POLICY)["ok"])
        self.assertFalse(dispatch({"tool": "read_file", "args": "x"}, POLICY)["ok"])


if __name__ == "__main__":
    unittest.main()
