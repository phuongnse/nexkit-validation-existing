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
preserved. Missing or blank text produces an empty value. `GET /health` returns
HTTP 200 with `{"status": "ok"}` as JSON. Unknown routes return HTTP 404 with
`{"error": "not_found"}`. The service listens on loopback only.

## Verify

```sh
python3 -m unittest discover -s tests -p test_unit.py -v
python3 -m unittest discover -s tests -p test_http.py -v
python3 -m unittest discover -s tests -p test_package.py -v
```

The HTTP suite launches the real application as a separate process and sends
requests over a local TCP socket. All suites must execute actual test cases.

## Prepare a local package

Run from the exact selected commit:

```sh
python3 scripts/package.py --version 0.1.0-test.1 --commit FULL_COMMIT_SHA
```

The deterministic ZIP contains `service.py`, this README and `SOURCE.json` with
the version, commit and source hashes. Extract it and run `python3 service.py`.
Packaging reads the selected Git blobs and refuses to replace an archive with
different bytes under the same version. It does not create a Git tag or release.
The package suite also extracts the ZIP and starts its actual HTTP application.

## Validation scope

This is a public acceptance fixture with no production data. Its baseline
behavior, commands and conventions provide inputs for NexKit setup. NexKit
delivery, model authentication and release are validated separately.
