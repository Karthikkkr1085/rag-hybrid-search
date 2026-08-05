import chromadb


class ChromaStore:

    def __init__(self):

        self.client = chromadb.PersistentClient(path="data/chroma_db")

        self.collection = self.client.get_or_create_collection(name="company_documents")

    def add_documents(self, chunks):
        """
        Store document chunks in ChromaDB.
        """

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for chunk in chunks:

            unique_id = f"{chunk['source']}_{chunk['page']}_{chunk['chunk_id']}"
            ids.append(unique_id)

            documents.append(chunk["text"])

            embeddings.append(chunk["embedding"])

            metadatas.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                }
            )

        self.collection.add(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

        print(f"✅ Stored {len(ids)} chunks in ChromaDB")

    def get_document_count(self):
        """
        Returns the number of stored documents.
        """
        return self.collection.count()
