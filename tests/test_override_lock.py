"""scripts/override_lock.py puts an overridden version, with its hashes, in place of the resolved one."""
import unittest

from scripts import override_lock

LOCK = """#
# header
#
mcp==1.29.0 \\
    --hash=sha256:aaaa \\
    --hash=sha256:bbbb
    # via semgrep
wcmatch==8.5.2 \\
    --hash=sha256:cccc
    # via semgrep
"""


class OverrideLockTests(unittest.TestCase):
    def test_replaces_the_entry_and_keeps_the_rest(self):
        out = override_lock.apply(LOCK, {"mcp": "1.30.0"}, get_hashes=lambda n, v: ["1111", "2222"], source="o.txt")
        self.assertIn("mcp==1.30.0 \\\n    --hash=sha256:1111 \\\n    --hash=sha256:2222\n    # via semgrep\n    # overridden by o.txt", out)
        self.assertNotIn("1.29.0", out)
        self.assertIn("wcmatch==8.5.2 \\\n    --hash=sha256:cccc\n    # via semgrep\n", out)
        self.assertTrue(out.startswith("#\n# header\n#\n"))
        # Running it again changes nothing.
        self.assertEqual(override_lock.apply(out, {"mcp": "1.30.0"}, get_hashes=lambda n, v: ["1111", "2222"], source="o.txt"), out)

    def test_an_override_the_lock_does_not_hold_is_an_error(self):
        with self.assertRaises(SystemExit):
            override_lock.apply(LOCK, {"jinja2": "3.1.6"}, get_hashes=lambda n, v: ["1111"])

    def test_reads_pins_and_skips_comments(self):
        self.assertEqual(override_lock.overrides("# why\nmcp==1.30.0\n\nwcmatch==11.2\n"), {"mcp": "1.30.0", "wcmatch": "11.2"})


if __name__ == "__main__":
    unittest.main()
