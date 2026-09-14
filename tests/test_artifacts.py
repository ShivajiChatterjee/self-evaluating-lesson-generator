import tempfile
import unittest
from pathlib import Path

from src.artifacts import _prepare_pdf_code_block, _write_pdf


class PdfDiagramRenderingTest(unittest.TestCase):
    def test_unicode_diagram_is_rendered_as_aligned_ascii(self) -> None:
        unicode_diagram = """┌────────────────┐
│   Retrieval    │
├────────────────┤
│   Generation   │
└────────────────┘
        │
        ▼ ►
"""
        expected_ascii = """+----------------+
|   Retrieval    |
+----------------+
|   Generation   |
+----------------+
        |
        v >
"""

        self.assertEqual(_prepare_pdf_code_block(unicode_diagram), expected_ascii)
        self.assertEqual(_prepare_pdf_code_block("print('ordinary code')\n"), "print('ordinary code')\n")

        markdown = f"# Diagram lesson\n\n```text\n{unicode_diagram}```\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "diagram.pdf"
            _write_pdf(markdown, "Diagram lesson", pdf_path)

            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF"))
            self.assertGreater(pdf_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
