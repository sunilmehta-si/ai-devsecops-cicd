import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from apps.llm_gateway.guard import ValidationError, redact_output, validate_chat_request
from apps.llm_gateway.server import make_handler

TEST_KEY = "test-key-for-unit-tests-only"  # secret-scan:allow


class GuardTests(unittest.TestCase):
    def test_rejects_bad_shapes(self):
        for payload in [None, [], {}, {"messages": []}, {"messages": ["x"]},
                        {"messages": [{"role": "root", "content": "hi"}]},
                        {"messages": [{"role": "user", "content": "  "}]},
                        {"messages": [{"role": "user", "content": "a" * 5000}]},
                        {"messages": [{"role": "user", "content": "hi"}] * 40}]:
            with self.subTest(payload=str(payload)[:40]), self.assertRaises(ValidationError):
                validate_chat_request(payload)

    def test_strips_control_characters(self):
        out = validate_chat_request({"messages": [{"role": "user", "content": "he\x00l\x07lo"}]})
        self.assertEqual(out[0]["content"], "hello")

    def test_redacts_credentials_in_output(self):
        leaked = "key is AKIA" + "ABCDEFGHIJKLMNOP now"
        self.assertNotIn("AKIA", redact_output(leaked))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(TEST_KEY))
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, body, key=TEST_KEY):
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=json.dumps(body).encode(), method="POST")
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as err:
            return err.code, json.load(err)

    def test_health(self):
        with urllib.request.urlopen(self.base + "/healthz") as resp:
            self.assertEqual(json.load(resp), {"status": "ok"})

    def test_requires_auth(self):
        self.assertEqual(self.post({"messages": []}, key=None)[0], 401)
        self.assertEqual(self.post({"messages": []}, key="wrong")[0], 401)

    def test_rejects_invalid_body(self):
        self.assertEqual(self.post({"messages": []})[0], 400)

    def test_happy_path(self):
        status, body = self.post({"messages": [{"role": "user", "content": "hello"}]})
        self.assertEqual(status, 200)
        self.assertIn("hello", body["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
