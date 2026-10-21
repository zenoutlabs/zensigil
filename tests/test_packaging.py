import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from tools.package_release import package
from tools.verify_release import verify


class PackagingTests(unittest.TestCase):
    def test_source_zip_is_reproducible_and_portable_examples_keep_contracts(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            first = package(Path(directory) / "first")
            second = package(Path(directory) / "second")
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(),
                             hashlib.sha256(second.read_bytes()).digest())
            verify(first.parent)
            verify(second.parent)


if __name__ == "__main__":
    unittest.main()
