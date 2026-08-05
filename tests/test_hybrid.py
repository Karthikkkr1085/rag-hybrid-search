from src.chunking.chunker import TextChunker
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.retrieval.hybrid import HybridSearch

loader = DocumentLoader()
parser = PDFParser()
cleaner = TextCleaner()
chunker = TextChunker()

documents = loader.load_documents()

pages = parser.parse(documents[0])

for page in pages:
    page["text"] = cleaner.clean_text(page["text"])

chunks = chunker.chunk(pages)

hybrid = HybridSearch(chunks, top_k=5)

results = hybrid.search("How many leave days are employees entitled to?")

print("=" * 60)
print("Hybrid Search Results")
print("=" * 60)

for i, result in enumerate(results, 1):

    print(f"\nResult {i}")

    print(f"Source : {result['metadata']['source']}")
    print(f"Page   : {result['metadata']['page']}")
    print(f"RRF Score : {result['score']:.5f}")

    print("-" * 50)

    print(result["document"][:350])
