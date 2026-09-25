"""Exercise actual Git snapshots, archive contents and the extracted HTTP app."""

import hashlib
import json
import selectors
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.request import urlopen

from scripts.package import ROOT, build, git


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="label-package-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        git(self.root, "init", "--quiet")
        for name in ("service.py", "README.md"):
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        self.commit()

    def commit(self):
        git(self.root, "add", "service.py", "README.md")
        git(
            self.root,
            "-c",
            "user.name=NexKit test",
            "-c",
            "user.email=nexkit@localhost",
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--quiet",
            "-m",
            "Package fixture",
        )
        self.sha = git(self.root, "rev-parse", "HEAD").decode().strip()

    def package(self):
        return build(self.root, "0.1.0-test.1", self.sha)

    def test_repeat_build_is_identical_and_records_source(self):
        first = self.package()
        artifact = Path(first["artifact"])
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o644)
        before = artifact.read_bytes()
        self.assertEqual(first["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.package()["sha256"], first["sha256"])
        self.assertEqual(artifact.read_bytes(), before)
        with zipfile.ZipFile(artifact) as archive:
            self.assertEqual(
                set(archive.namelist()), {"README.md", "service.py", "SOURCE.json"}
            )
            source = json.loads(archive.read("SOURCE.json"))
            self.assertEqual(first["source"], source)
            self.assertEqual(source["commit"], self.sha)
            self.assertEqual(source["version"], "0.1.0-test.1")
            for name in ("README.md", "service.py"):
                self.assertEqual(
                    archive.read(name), git(self.root, "show", f"{self.sha}:{name}")
                )
                self.assertEqual(
                    hashlib.sha256(archive.read(name)).hexdigest(),
                    source["sha256"][name],
                )

    def test_reused_archive_is_readable_by_separate_collector(self):
        first = self.package()
        artifact = Path(first["artifact"])
        before = artifact.read_bytes()
        artifact.chmod(0o600)
        second = self.package()
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o644)
        self.assertEqual(artifact.read_bytes(), before)
        self.assertEqual(second, first)

    def test_local_edits_do_not_change_selected_source(self):
        (self.root / "service.py").write_text("This is not the committed source")
        with zipfile.ZipFile(self.package()["artifact"]) as archive:
            self.assertEqual(
                archive.read("service.py"),
                git(self.root, "show", f"{self.sha}:service.py"),
            )

    def test_invalid_identity_and_path_are_rejected(self):
        for version, sha in (("../escape", self.sha), ("0.1.0-test.1", "0" * 40)):
            with self.subTest(version=version, sha=sha), self.assertRaises(ValueError):
                build(self.root, version, sha)
        self.assertFalse((self.root / "dist").exists())

    def test_existing_different_archive_is_preserved(self):
        artifact = Path(self.package()["artifact"])
        original = artifact.read_bytes()
        (self.root / "README.md").write_text("A changed committed document\n")
        self.commit()
        with self.assertRaisesRegex(ValueError, "different bytes"):
            self.package()
        self.assertEqual(artifact.read_bytes(), original)

    def test_extracted_archive_serves_real_http(self):
        unpacked = self.root / "unpacked"
        with zipfile.ZipFile(self.package()["artifact"]) as archive:
            archive.extractall(unpacked)
        process = subprocess.Popen(
            [sys.executable, "service.py", "--port", "0"],
            cwd=unpacked,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(
                    selector.select(timeout=5), "Packaged service did not start"
                )
                base = process.stdout.readline().strip()
            self.assertTrue(base.startswith("http://127.0.0.1:"), base)
            with urlopen(base + "/normalize?text=Hello%20WORLD", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response), {"value": "hello-world"})
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
