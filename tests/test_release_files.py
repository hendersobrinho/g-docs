from __future__ import annotations

from pathlib import Path
import re
import unittest

from documentos_empresa_app import __version__


ROOT_DIR = Path(__file__).resolve().parents[1]
README_PATH = ROOT_DIR / "README.md"
INSTALLER_PATH = ROOT_DIR / "installer" / "G-docs.iss"


class ReleaseFileTests(unittest.TestCase):
    def test_readme_version_matches_package_version(self) -> None:
        readme_text = README_PATH.read_text(encoding="utf-8")
        self.assertIn(f"Versao atual: `{__version__}`", readme_text)

    def test_installer_version_matches_package_version(self) -> None:
        installer_text = INSTALLER_PATH.read_text(encoding="utf-8")
        match = re.search(r'#define AppVersion "([^"]+)"', installer_text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), __version__)


if __name__ == "__main__":
    unittest.main()
