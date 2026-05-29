import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_embedding(text: str) -> list[float]:
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    return response.embeddings[0].values


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
    context_parts = [f"[Kaynak: {c['document']}, Sayfa {c['page']}]\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(context_parts), sources
