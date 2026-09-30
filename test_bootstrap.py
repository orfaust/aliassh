import io
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_downloads_both_files_and_invokes_installer(self):
        def fetch(url, timeout):
            self.assertEqual(timeout, 20)
            self.assertTrue(url.startswith(bootstrap.RAW_BASE))
            name = url.rsplit("/", 1)[-1]
            return io.BytesIO(f"# {name}\n".encode())

        def invoke(command):
            installer = Path(command[1])
            self.assertEqual(command[0], bootstrap.sys.executable)
            self.assertEqual(installer.read_text(), "# install.py\n")
            self.assertEqual((installer.parent / "alias_connect.py").read_text(), "# alias_connect.py\n")
            return 0

        with patch.object(bootstrap.urllib.request, "urlopen", side_effect=fetch) as get, \
             patch.object(bootstrap.subprocess, "call", side_effect=invoke) as run:
            self.assertEqual(bootstrap.bootstrap(), 0)
            self.assertEqual(get.call_count, 2)
            run.assert_called_once()

    def test_download_failure_does_not_run_installer(self):
        with patch.object(bootstrap.urllib.request, "urlopen", side_effect=OSError("offline")), \
             patch.object(bootstrap.subprocess, "call") as run:
            self.assertEqual(bootstrap.bootstrap(), 1)
            run.assert_not_called()

    def test_oversized_download_does_not_run_installer(self):
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(b"x" * (bootstrap.MAX_FILE_BYTES + 1))), \
             patch.object(bootstrap.subprocess, "call") as run:
            self.assertEqual(bootstrap.bootstrap(), 1)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
