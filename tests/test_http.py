"""Exercise the actual service command through HTTP requests."""

import json
import selectors
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(
            [sys.executable, "service.py", "--port", "0"],
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls.addClassCleanup(cls.stop_service)
        with selectors.DefaultSelector() as selector:
            selector.register(cls.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=5):
                raise AssertionError("The service did not announce its address within five seconds")
            cls.base = cls.process.stdout.readline().strip()
        if not cls.base.startswith("http://127.0.0.1:"):
            raise AssertionError(f"Unexpected service address: {cls.base!r}")

    @classmethod
    def stop_service(cls):
        if cls.process.poll() is None:
            cls.process.terminate()
        try:
            cls.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.communicate(timeout=5)

    def get(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            body = response.read()
            self.assertEqual(int(response.headers["Content-Length"]), len(body))
            return json.loads(body)

    def test_normalization_response(self):
        query = urlencode({"text": "  Hello   WORLD  "})
        self.assertEqual(self.get("/normalize?" + query), {"value": "hello-world"})

    def test_blank_text(self):
        self.assertEqual(self.get("/normalize?text="), {"value": ""})

    def test_missing_text(self):
        self.assertEqual(self.get("/normalize"), {"value": ""})

    def test_encoded_unicode(self):
        query = urlencode({"text": "CAFÉ Label"})
        self.assertEqual(self.get("/normalize?" + query), {"value": "café-label"})

    def test_unknown_route(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + "/missing", timeout=5)
        with raised.exception as response:
            self.assertEqual(response.code, 404)
            self.assertEqual(json.load(response), {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
