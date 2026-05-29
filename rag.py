import os, requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def get_embedding(text: str) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY"
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()["embedding"]["values"]

def retrieve(query: str, n_results: int = 5) -> list[dict]:
    embedding = get_embedding(query)
    result = sb.rpc("match_documents", {
        "query_embedding": embedding,
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
    parts = [f"[Kaynak: {c['document']}, Sayfa {c['page']}]\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(parts), sources
