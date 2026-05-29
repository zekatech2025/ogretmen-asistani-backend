import os
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def retrieve(query: str, n_results: int = 5) -> list[dict]:
    embedder = get_embedder()
    query_embedding = embedder.encode(query).tolist()

    # Supabase pgvector benzerlik araması
    result = sb.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_threshold": 0.3,
        "match_count": n_results
    }).execute()

    chunks = []
    for row in (result.data or []):
        chunks.append({
            "text": row["content"],
            "document": row["metadata"].get("document", "Bilinmeyen Belge"),
            "page": row["metadata"].get("page", 0),
            "score": round(row.get("similarity", 0), 3)
        })

    return chunks


def build_context(chunks: list[dict]) -> tuple[str, list[str]]:
    if not chunks:
        return "", []

    sources = list({c["document"] for c in chunks})
    context_parts = []
    for c in chunks:
        context_parts.append(
            f"[Kaynak: {c['document']}, Sayfa {c['page']}]\n{c['text']}"
        )

    return "\n\n---\n\n".join(context_parts), sources
