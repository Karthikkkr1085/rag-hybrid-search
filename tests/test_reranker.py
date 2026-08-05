from src.chunking.chunker import TextChunker
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.retrieval.hybrid import HybridSearch
from src.retrieval.reranker import Reranker


def main():

    # -----------------------------
    # Ingestion Pipeline
    # -----------------------------
    loader = DocumentLoader()
    parser = PDFParser()
    cleaner = TextCleaner()
    chunker = TextChunker()

    documents = loader.load_documents()

    pages = parser.parse(documents[0])

    for page in pages:
        page["text"] = cleaner.clean_text(page["text"])

    chunks = chunker.chunk(pages)

    # -----------------------------
    # Hybrid Search
    # -----------------------------
    hybrid = HybridSearch(chunks=chunks, top_k=5)

    query = "How many leave days are employees entitled to?"

    hybrid_results = hybrid.search(query)

    # -----------------------------
    # Reranker
    # -----------------------------
    reranker = Reranker()

    reranked_results = reranker.rerank(query=query, results=hybrid_results, top_k=3)

    # -----------------------------
    # Display Results
    # -----------------------------
    print("=" * 60)
    print("Reranked Results")
    print("=" * 60)

    for i, result in enumerate(reranked_results, start=1):

        print(f"\nResult {i}")
        print(f"Source : {result['metadata']['source']}")
        print(f"Page   : {result['metadata']['page']}")
        print(f"Score  : {result['rerank_score']:.4f}")

        print("-" * 50)

        print(result["document"][:400])


if __name__ == "__main__":
    main()
