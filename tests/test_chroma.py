from src.vectordb.chroma_store import ChromaStore

store = ChromaStore()

print(store.collection.name)
