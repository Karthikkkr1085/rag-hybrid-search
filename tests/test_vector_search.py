from src.retrieval.vector_search import VectorSearch

search = VectorSearch(top_k=3)

query = "How many leave days are employees entitled to?"

results = search.search(query)

print("=" * 60)
print("Vector Search Results")
print("=" * 60)

documents = results["documents"][0]
metadatas = results["metadatas"][0]
distances = results["distances"][0]

for i, (doc, meta, distance) in enumerate(
    zip(documents, metadatas, distances), start=1
):
    print(f"\nResult {i}")
    print(f"Source   : {meta['source']}")
    print(f"Page     : {meta['page']}")
    print(f"Distance : {distance:.4f}")
    print("-" * 50)
    print(doc[:300])
