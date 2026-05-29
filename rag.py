import os
import google.generativeai as genai
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


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
    context_parts = []
    for c in chunks:
        context_parts.append(
            f"[Kaynak: {c['document']}, Sayfa {c['page']}]\n{c['text']}"
        )

    return "\n\n---\n\n".join(context_parts), sources
