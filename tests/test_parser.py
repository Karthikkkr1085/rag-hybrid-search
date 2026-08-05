from src.chunking.chunker import TextChunker
from src.embeddings.embedding import EmbeddingGenerator
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.vectordb.chroma_store import ChromaStore

# Initialize classes
loader = DocumentLoader()
parser = PDFParser()
cleaner = TextCleaner()
chunker = TextChunker()
embedder = EmbeddingGenerator()
store = ChromaStore()

# Load PDF files
documents = loader.load_documents()

# Parse the first PDF
pages = parser.parse(documents[0])

# Clean every page
for page in pages:
    page["text"] = cleaner.clean_text(page["text"])

# Create chunks
chunks = chunker.chunk(pages)

# Display results
print("\n" + "=" * 60)
print(f"Document : {documents[0].name}")
print(f"Total Pages : {len(pages)}")
print(f"Total Chunks : {len(chunks)}")
print("=" * 60)

print("\nFirst Chunk Metadata")
print("-" * 30)
print(f"Chunk ID : {chunks[0]['chunk_id']}")
print(f"Source   : {chunks[0]['source']}")
print(f"Page     : {chunks[0]['page']}")

print("\nChunk Preview")
print("-" * 30)
print(chunks[0]["text"][:500])

# Generate embeddings
embedded_chunks = embedder.generate_embeddings(chunks)

print("\n" + "=" * 60)
print("Embedding Test")
print("=" * 60)

print(f"Total Chunks : {len(embedded_chunks)}")
print(f"Embedding Dimension : {len(embedded_chunks[0]['embedding'])}")

print("\nFirst 10 Embedding Values")
print(embedded_chunks[0]["embedding"][:10])

# Store chunks in ChromaDB
store.add_documents(embedded_chunks)

print(f"\nTotal Documents in ChromaDB : {store.get_document_count()}")
