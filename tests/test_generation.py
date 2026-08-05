from dotenv import load_dotenv

load_dotenv()

from src.chunking.chunker import TextChunker
from src.embeddings.embedding import EmbeddingGenerator
from src.generation.generator import Generator
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.retrieval.hybrid import HybridSearch
from src.retrieval.reranker import Reranker
from src.vectordb.chroma_store import ChromaStore

# ==========================================
# Load Documents
# ==========================================

loader = DocumentLoader("docs")
documents = loader.load_documents()

parser = PDFParser()
cleaner = TextCleaner()
chunker = TextChunker()

chunks = []

for document in documents:

    # Parse PDF
    pages = parser.parse(document)

    # Clean pages
    for page in pages:
        page["text"] = cleaner.clean_text(page["text"])

    # Create chunks
    chunks.extend(chunker.chunk(pages))

print(f"\n✅ Total Chunks Created: {len(chunks)}")
# ==========================================
# Generate Embeddings
# ==========================================

embedder = EmbeddingGenerator()
chunks = embedder.generate_embeddings(chunks)
import json
import os

os.makedirs("data", exist_ok=True)

with open("data/chunks/chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print("✅ Chunks saved to data/chunks.json")
# ==========================================
# Store in ChromaDB
# ==========================================

# ==========================================
# Store in ChromaDB
# ==========================================

# Delete old collection (if it exists)
try:
    temp_store = ChromaStore()
    temp_store.client.delete_collection("company_documents")
except Exception:
    pass

# Create a fresh collection
store = ChromaStore()

# Add documents
store.add_documents(chunks)

print("Documents in ChromaDB:", store.get_document_count())
print("\n==============================")
print("ALL LEAVE CHUNKS")
print("==============================")

for chunk in chunks:
    text = chunk["text"].lower()

    if any(
        keyword in text
        for keyword in [
            "leave",
            "days",
            "casual",
            "privilege",
            "sick",
            "annual",
            "maternity",
            "paternity",
        ]
    ):
        print("\n-----------------------------------")
        print("Source :", chunk["source"])
        print("Page   :", chunk["page"])
        print(chunk["text"])
# ==========================================
# Retrieval
# ==========================================

hybrid = HybridSearch(chunks=chunks, top_k=20)
reranker = Reranker()


# ==========================================
# Generator
# ==========================================

generator = Generator()


# ==========================================
# User Query
# ==========================================

query = "How many leave days are employees entitled to?"

print(f"\nQuery: {query}")


# ==========================================
# Hybrid Search
# ==========================================

results = hybrid.search(query)

print(f"\nRetrieved Documents: {len(results)}")

print("\n==============================")
print("HYBRID SEARCH RESULTS")
print("==============================")

for i, r in enumerate(results, 1):
    print("=" * 80)
    print(f"Rank: {i}")
    print("Metadata:", r["metadata"])
    print("Document:")
    print(r["document"])

# ==========================================
# Reranking
# ==========================================

# Disable reranker for testing
# results = results[:6]
# ==========================================
# Reranking
# ==========================================

results = reranker.rerank(query=query, results=results, top_k=8)

print("\n==============================")
print("RETRIEVED CONTEXT")
print("==============================")

for i, result in enumerate(results, start=1):
    print(f"\n------ Document {i} ------")
    print("Source:", result["metadata"]["source"])
    print("Page:", result["metadata"]["page"])
    print(result["document"])

print(f"Top Documents After Reranking: {len(results)}")


# ==========================================
# Generation
# ==========================================

response = generator.generate(query=query, contexts=results)


# ==========================================
# Output
# ==========================================

print("\n==============================")
print("ANSWER")
print("==============================")
print(response["answer"])

print("\n==============================")
print("VERIFIED")
print("==============================")
print(response["verified"])

print("\n==============================")
print("CITATIONS")
print("==============================")

for citation in response["citations"]:
    print(f'{citation["source"]} (Page {citation["page"]})')
