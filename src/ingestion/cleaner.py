import re
from pathlib import Path


class TextCleaner:
    """
    Cleans extracted PDF text and saves processed files.
    """

    def clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text (str): Raw extracted text.

        Returns:
            str: Cleaned text.
        """

        # ==========================================
        # Remove PDF bullet/encoding artifacts
        # ==========================================

        text = text.replace("", "•")
        text = text.replace("", "•")
        text = text.replace("◦", "•")

        # Remove private-use unicode characters
        text = re.sub(r"[\uE000-\uF8FF]", "", text)

        # Remove zero-width characters
        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

        # ==========================================
        # Normalize whitespace
        # ==========================================

        # Replace multiple spaces and tabs with a single space
        text = re.sub(r"[ \t]+", " ", text)

        # Replace multiple blank lines with a maximum of one blank line
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        # Remove leading and trailing whitespace
        text = text.strip()

        return text

    def save_processed_text(self, pages, output_dir="data/processed"):
        """
        Save cleaned text into a .txt file.

        Args:
            pages (list): Parsed pages from PDFParser.
            output_dir (str): Directory to save processed text.
        """

        if not pages:
            print("No pages to save.")
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get filename from parser output
        filename = pages[0]["filename"].replace(".pdf", ".txt")

        file_path = output_path / filename

        with open(file_path, "w", encoding="utf-8") as file:

            for page in pages:
                cleaned_text = self.clean_text(page["text"])

                file.write(f"========== PAGE {page['page']} ==========\n")
                file.write(cleaned_text)
                file.write("\n\n")

        print(f"✅ Processed file saved to: {file_path}")
