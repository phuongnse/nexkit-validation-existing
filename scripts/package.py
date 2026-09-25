"""Build a deterministic local archive from the exact selected Git commit."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.PIPE
    )


def build(root, version, commit):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("Version must be a plain semantic version or prerelease")
    if len(version) > 80 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Provide a short version and a full lowercase commit SHA")
    if git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("The checkout does not match the selected commit")
    # Read committed blobs so local build outputs or edited files cannot drift
    # the packaged source away from the selected candidate.
    files = {
        name: git(root, "show", f"{commit}:{name}")
        for name in ("README.md", "service.py")
    }
    source = {
        "repository": "phuongnse/nexkit-validation-existing",
        "version": version,
        "commit": commit,
        "sha256": {
            name: hashlib.sha256(data).hexdigest() for name, data in files.items()
        },
    }
    files["SOURCE.json"] = (
        json.dumps(source, indent=2, sort_keys=True) + "\n"
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    data = buffer.getvalue()
    destination = root / "dist"
    if destination.is_symlink():
        raise ValueError("The output directory must not be a symlink")
    destination.mkdir(exist_ok=True)
    target = destination / f"label-service-{version}.zip"
    if target.is_symlink():
        raise ValueError("The output file must not be a symlink")
    with tempfile.NamedTemporaryFile(dir=destination, prefix=".package-") as staged:
        # The separate Actions artifact collector must be able to read the ZIP.
        os.fchmod(staged.fileno(), 0o644)
        staged.write(data)
        staged.flush()
        try:
            # Atomic creation without replacing another build's artifact.
            os.link(staged.name, target)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != data:
                raise ValueError(
                    "An existing archive has different bytes; inspect it before replacing it"
                ) from None
            target.chmod(0o644, follow_symlinks=False)
    return {
        "artifact": str(target),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source": source,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        result = build(ROOT, args.version, args.commit)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
