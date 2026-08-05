from dotenv import load_dotenv

load_dotenv()

import json
import os

from src.chunking.chunker import TextChunker
from src.embeddings.embedding import EmbeddingGenerator
from src.ingestion.cleaner import TextCleaner
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import PDFParser
from src.utils.logging_config import logger
from src.vectordb.chroma_store import ChromaStore

# Load Documents
loader = DocumentLoader("docs")
documents = loader.load_documents()

parser = PDFParser()
cleaner = TextCleaner()
chunker = TextChunker()

chunks = []

for document in documents:
    pages = parser.parse(document)

    for page in pages:
        page["text"] = cleaner.clean_text(page["text"])

    chunks.extend(chunker.chunk(pages))

logger.info(f"Total Chunks Created: {len(chunks)}")

# Generate Embeddings
embedder = EmbeddingGenerator()
chunks = embedder.generate_embeddings(chunks)

# Save chunks.json
os.makedirs("data/chunks", exist_ok=True)

with open("data/chunks/chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

logger.info("Chunks saved to data/chunks/chunks.json")

# Store in ChromaDB
try:
    temp_store = ChromaStore()
    temp_store.client.delete_collection("company_documents")
except Exception:
    pass

store = ChromaStore()
store.add_documents(chunks)

logger.info(f"Documents in ChromaDB: {store.get_document_count()}")
logger.info("Documents Indexed Successfully")
