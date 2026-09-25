# Label service

A small Python HTTP application prepared as an existing repository for NexKit
acceptance. This baseline is committed before NexKit is installed.

## Requirements

Python 3.12 or newer. The application and tests use only the standard library.

## Run

```sh
python3 service.py --port 8000
curl 'http://127.0.0.1:8000/normalize?text=Hello%20World'
```

`GET /normalize?text=...` returns a JSON object such as
`{"value": "hello-world"}`. Normalization lowercases text, removes surrounding
whitespace and joins whitespace-separated words with hyphens. Punctuation is
preserved. Missing or blank text produces an empty value. Unknown routes return
HTTP 404 with `{"error": "not_found"}`. The service listens on loopback only.

## Verify

```sh
python3 -m unittest discover -s tests -p test_unit.py -v
python3 -m unittest discover -s tests -p test_http.py -v
```

The HTTP suite launches the real application as a separate process and sends
requests over a local TCP socket. Both suites must execute actual test cases.

## Validation scope

This is a private acceptance fixture with no production data. Its baseline
behavior, commands and conventions provide inputs for NexKit setup. NexKit
delivery, model authentication and release are validated separately.
