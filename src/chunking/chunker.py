import os

from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextChunker:
    """
    Splits cleaned PDF text into smaller chunks while preserving metadata.
    """

    def __init__(self, chunk_size=None, chunk_overlap=None):

        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", 1200))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", 300))

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[
                "\n# ",
                "\n## ",
                "\n### ",
                "\n\n",
                "\n",
                ". ",
                "; ",
                ": ",
                ", ",
                " ",
                "",
            ],
            length_function=len,
        )

    def chunk(self, pages):
        """
        Split parsed pages into chunks.

        Args:
            pages (list): List of parsed PDF pages.

        Returns:
            list: List of chunk dictionaries.
        """

        chunks = []
        chunk_id = 1

        for page in pages:

            split_texts = self.text_splitter.split_text(page["text"])

            for text in split_texts:

                document_text = text.strip()

                if page["page"] > 1:
                    document_text = f"{page['filename']}\n{document_text}"

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "source": page["filename"],
                        "page": page["page"],
                        "text": document_text,
                        "length": len(document_text),
                    }
                )

                chunk_id += 1

        return chunks
