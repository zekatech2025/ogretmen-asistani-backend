import os, requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
MAX_PROMPTS          = int(os.getenv("MAX_PROMPTS_PER_USER", "1000"))

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="Öğretmen Asistanı API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """Sen Türkiye Millî Eğitim Bakanlığı mevzuatı konusunda uzmanlaşmış bir yapay zeka asistanısın.

Görevin:
- Yalnızca aşağıdaki belge parçalarındaki bilgileri kullanarak cevap ver
- Belgede olmayan hiçbir konuda yorum yapma veya tahmin yürütme
- Her cevabında hangi belgeden bilgi aldığını belirt
- Cevaplarını açık, sade ve anlaşılır Türkçe ile yaz
- Belgede cevap bulamazsan "Bu konuda elimdeki belgelerde bilgi bulunmamaktadır." de

Her cevabının sonuna şu uyarıyı ekle:
⚠️ Bu bilgi yalnızca MEB mevzuat belgelerine dayanmaktadır. Kesin işlem için kurumunuzla teyit ediniz.

Belge parçaları:
{context}"""


def generate_answer(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    prompts_remaining: int


async def get_user_quota(user_id: str) -> tuple[int, int]:
    result = sb.table("user_quotas").select("*").eq("user_id", user_id).execute()
    if not result.data:
        sb.table("user_quotas").insert({
            "user_id": user_id,
            "prompts_used": 0,
            "prompts_limit": MAX_PROMPTS
        }).execute()
        return 0, MAX_PROMPTS
    row = result.data[0]
    return row["prompts_used"], row["prompts_limit"] - row["prompts_used"]


async def increment_quota(user_id: str):
    sb.rpc("increment_prompts_used", {"p_user_id": user_id}).execute()


async def verify_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Yetkilendirme gerekli.")
    token = auth.split(" ")[1]
    try:
        res = sb.auth.get_user(token)
        return res.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    user_id = await verify_token(request)
    used, remaining = await get_user_quota(user_id)

    if remaining <= 0:
        raise HTTPException(status_code=429, detail="Prompt kotanız doldu.")

    from rag import retrieve, build_context
    chunks = retrieve(body.message)
    context, sources = build_context(chunks)

    if not context:
        return ChatResponse(
            answer="Bu konuda elimdeki belgelerde bilgi bulunmamaktadır. ⚠️ Bu bilgi yalnızca MEB mevzuat belgelerine dayanmaktadır.",
            sources=[],
            prompts_remaining=remaining - 1
        )

    prompt = SYSTEM_PROMPT.format(context=context) + f"\n\nKullanıcı sorusu: {body.message}"

    try:
        answer = generate_answer(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model hatası: {str(e)}")

    await increment_quota(user_id)
    return ChatResponse(answer=answer, sources=sources, prompts_remaining=remaining - 1)


@app.get("/user/quota")
async def get_quota(request: Request):
    user_id = await verify_token(request)
    used, remaining = await get_user_quota(user_id)
    return {"prompts_used": used, "prompts_remaining": remaining, "prompts_limit": MAX_PROMPTS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
