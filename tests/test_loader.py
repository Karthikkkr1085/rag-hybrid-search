from src.ingestion.loader import DocumentLoader

loader = DocumentLoader()

documents = loader.load_documents()

print("Documents Found:\n")

for document in documents:
    print(document.name)

print(f"\nTotal Documents: {len(documents)}")
