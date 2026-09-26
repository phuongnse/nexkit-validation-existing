"""Helpers for assertions that need to inspect raw HTTP response bytes."""

import socket
from urllib.parse import urlsplit


def raw_head_response(base, path):
    parsed = urlsplit(base)
    with socket.create_connection(
        (parsed.hostname, parsed.port), timeout=5
    ) as connection:
        connection.settimeout(5)
        connection.sendall(
            f"HEAD {path} HTTP/1.0\r\nHost: {parsed.hostname}\r\n\r\n".encode()
        )
        chunks = []
        while chunk := connection.recv(4096):
            chunks.append(chunk)

    response = b"".join(chunks)
    header_block, separator, body = response.partition(b"\r\n\r\n")
    if not separator:
        raise AssertionError(f"Malformed HTTP response: {response!r}")
    status_line, *header_lines = header_block.split(b"\r\n")
    headers = {
        name.decode("ascii").lower(): value.decode("ascii").strip()
        for name, value in (line.split(b":", 1) for line in header_lines)
    }
    return int(status_line.split()[1]), headers, body
