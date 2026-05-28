import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=GEMINI_API_KEY,
            model_name="models/text-embedding-004"
        )
        _collection = _client.get_or_create_collection(
            name="meb_mevzuat",
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def retrieve(query: str, n_results: int = 5) -> list[dict]:
    """
    Soruya en yakın PDF parçalarını döner.
    """
    collection = get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        # Çok uzak sonuçları filtrele (cosine distance > 0.7)
        if distance < 0.7:
            chunks.append({
                "text": doc,
                "document": meta.get("document", "Bilinmeyen Belge"),
                "page": meta.get("page", 0),
                "score": round(1 - distance, 3)
            })

    return chunks


def build_context(chunks: list[dict]) -> tuple[str, list[str]]:
    """
    Chunk'lardan model için bağlam metni ve kaynak listesi oluşturur.
    """
    if not chunks:
        return "", []

    context_parts = []
    sources = list({c["document"] for c in chunks})  # Tekrarsız kaynaklar

    for c in chunks:
        context_parts.append(
            f"[Kaynak: {c['document']}, Sayfa {c['page']}]\n{c['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)
    return context, sources
