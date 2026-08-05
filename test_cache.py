from src.cache.cache_store import CacheStore
from src.embeddings.embedding import EmbeddingGenerator

store = CacheStore()
embedder = EmbeddingGenerator()

query = "Explain the leave policy"

embedding = embedder.generate_query_embedding(query)

result = store.search(embedding)

if result:
    print("\n✅ CACHE HIT")
    print(result)
else:
    print("\n❌ CACHE MISS")
