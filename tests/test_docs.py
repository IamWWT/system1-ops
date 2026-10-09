"""The documentation gate resolves versioned names without hiding broken links."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.doc_check import resolve


class DocumentationGate(unittest.TestCase):
    def test_versioned_wiki_name_and_missing_target(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "docs/02-design/SAD-system1_HD_0.2.0.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Architecture", encoding="utf-8")
            source = root / "docs/README.md"
            self.assertEqual(resolve(root, source, "02-design/SAD-system1_HD_0.2.0|Architecture", True), target)
            missing = resolve(root, source, "02-design/missing", True)
            self.assertFalse(missing.exists())
