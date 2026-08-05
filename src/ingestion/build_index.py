import json
from pathlib import Path

from src.chunking.chunker import TextChunker
from src.embeddings.embedding import EmbeddingGenerator
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.vectordb.chroma_store import ChromaStore


def build_index() -> list[dict]:
    """Rebuild the searchable index from every PDF in ``docs``."""
    loader = DocumentLoader()
    parser = PDFParser()
    cleaner = TextCleaner()
    chunker = TextChunker()
    embedder = EmbeddingGenerator()
    store = ChromaStore()

    pdf_files = loader.load_documents()

    all_chunks = []

    for pdf_file in pdf_files:

        pages = parser.parse(pdf_file)

        for page in pages:
            page["text"] = cleaner.clean_text(page["text"])

        # Extract only document metadata from the first page
        header_lines = []

        for line in pages[0]["text"].splitlines():
            line = line.strip()

            if (
                line.startswith("Ref:")
                or line.startswith("Revision:")
                or line.startswith("Effective")
                or line.upper() == "HR / LEAVE POLICY"
            ):
                header_lines.append(line)

        header = "\n".join(header_lines)

        # Prefix only the metadata to later pages
        for page in pages[1:]:
            page["text"] = f"{header}\n\n{page['text']}"

        chunks = chunker.chunk(pages)

        chunks = embedder.generate_embeddings(chunks)

        all_chunks.extend(chunks)

    Path("data/chunks").mkdir(parents=True, exist_ok=True)

    with open("data/chunks/chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=4, ensure_ascii=False)

    try:
        store.client.delete_collection("company_documents")
    except Exception:
        pass

    store = ChromaStore()

    store.add_documents(all_chunks)

    print(f"\nTotal Chunks : {len(all_chunks)}")
    print(f"Chroma Count : {store.get_document_count()}")
    return all_chunks


def main():
    build_index()


if __name__ == "__main__":
    main()
