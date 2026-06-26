import chromadb
import sys

sys.path.append("..")

from knowledge_base.medical_data import MEDICAL_KNOWLEDGE
from config import CHROMA_DB_PATH, COLLECTION_NAME, TOP_K_RESULTS


def setup_vector_db():
    """Run once to load medical knowledge into ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[item["id"] for item in MEDICAL_KNOWLEDGE],
        documents=[item["text"] for item in MEDICAL_KNOWLEDGE],
        metadatas=[
            {
                "parameter": item["parameter"],
                "condition": item["condition"],
                "specialist": item["specialist"],
                "urgency": item["urgency"],
            }
            for item in MEDICAL_KNOWLEDGE
        ],
    )

    return collection


def get_vector_db():
    """Get existing ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return setup_vector_db()


def search_medical_knowledge(query, n_results=TOP_K_RESULTS):
    """Search knowledge base for a given test value query."""
    collection = get_vector_db()

    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    output = []

    if not results or not results.get("documents"):
        return output

    for i in range(len(results["documents"][0])):
        output.append(
            {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
            }
        )

    return output


if __name__ == "__main__":
    setup_vector_db()
    results = search_medical_knowledge("TSH is 8.2 which is high")

    for r in results:
        print(f"Condition: {r['metadata']['condition']}")
        print(f"Specialist: {r['metadata']['specialist']}")
        print()