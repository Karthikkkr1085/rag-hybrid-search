from pathlib import Path

import fitz  # PyMuPDF


class PDFParser:
    """
    Extract text from PDF files page by page.
    """

    def parse(self, pdf_path: Path):
        """
        Parse a PDF file and extract text from each page.

        Args:
            pdf_path (Path): Path to the PDF file.

        Returns:
            list: List of dictionaries containing page data.
        """

        pages = []

        with fitz.open(pdf_path) as pdf:

            for page_number, page in enumerate(pdf, start=1):

                text = page.get_text("text").strip()

                pages.append(
                    {
                        "filename": pdf_path.name,
                        "page": page_number,
                        "text": text,
                    }
                )

        print("\n========== PARSED PAGES ==========\n")

        for page in pages:
            print(f"{page['filename']} | Page {page['page']}")
            print(page["text"][:300])
            print("-" * 100)

        return pages
