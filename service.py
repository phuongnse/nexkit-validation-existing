"""Normalize labels through a small loopback HTTP service."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit


def normalize(value: str) -> str:
    """Lowercase and join whitespace-separated words, preserving punctuation."""
    return "-".join(value.lower().split())


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request = urlsplit(self.path)
        if request.path != "/normalize":
            self.respond(404, {"error": "not_found"})
            return
        value = parse_qs(request.query, keep_blank_values=True).get("text", [""])[0]
        self.respond(200, {"value": normalize(value)})

    def respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
