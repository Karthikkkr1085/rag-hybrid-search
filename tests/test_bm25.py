from src.chunking.chunker import TextChunker
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.retrieval.bm25_search import BM25Search


def main():
    # Initialize components
    loader = DocumentLoader()
    parser = PDFParser()
    cleaner = TextCleaner()
    chunker = TextChunker()
    bm25 = BM25Search()

    # Load PDF files
    documents = loader.load_documents()

    # Parse first PDF
    pages = parser.parse(documents[0])

    # Clean pages
    for page in pages:
        page["text"] = cleaner.clean_text(page["text"])

    # Create chunks
    chunks = chunker.chunk(pages)

    print("=" * 60)
    print(f"Document      : {documents[0].name}")
    print(f"Total Pages   : {len(pages)}")
    print(f"Total Chunks  : {len(chunks)}")
    print("=" * 60)

    # Build BM25 index
    bm25.index_documents(chunks)

    # Query
    query = "How many leave days are employees entitled to?"

    print(f"\nQuery: {query}")

    results = bm25.search(query, top_k=3)

    print("\n" + "=" * 60)
    print("BM25 Search Results")
    print("=" * 60)

    for i, result in enumerate(results, start=1):

        print(f"\nResult {i}")
        print("-" * 50)

        print(f"Source : {result['metadata']['source']}")
        print(f"Page   : {result['metadata']['page']}")
        print(f"Score  : {result['score']:.4f}")

        print("\nPreview:\n")
        print(result["document"][:400])


if __name__ == "__main__":
    main()
