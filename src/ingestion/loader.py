from pathlib import Path


class DocumentLoader:
    """
    Loads PDF documents from the docs directory.
    """

    def __init__(self, documents_path: str = "docs"):
        self.documents_path = Path(documents_path)

    def load_documents(self):
        """
        Load all PDF files from the docs directory.

        Returns:
            list[Path]: List of PDF file paths.
        """

        if not self.documents_path.exists():
            raise FileNotFoundError(
                f"Directory '{self.documents_path}' does not exist."
            )

        pdf_files = list(self.documents_path.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in '{self.documents_path}'.")

        print(f"\n✅ Found {len(pdf_files)} PDF file(s):\n")

        for pdf in pdf_files:
            print(pdf.name)

        return pdf_files
