import os, sys, argparse, fitz, requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def get_embedding(text: str) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_DOCUMENT"
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()["embedding"]["values"]

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i+1, "text": text})
    doc.close()
    return pages

def chunk_text(pages, doc_name, chunk_size=300, overlap=50):
    chunks = []
    chunk_id = 0
    for p in pages:
        words = p["text"].split()
        i = 0
        while i < len(words):
            text = " ".join(words[i:i+chunk_size])
            if len(text) > 50:
                chunks.append({"text": text, "metadata": {"document": doc_name, "page": p["page"], "chunk": chunk_id}})
                chunk_id += 1
            i += chunk_size - overlap
    return chunks

def index_pdf(pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n📄 İşleniyor: {doc_name}")
    sb.table("documents").delete().eq("metadata->>document", doc_name).execute()
    pages = extract_text(pdf_path)
    chunks = chunk_text(pages, doc_name)
    print(f"  🔄 {len(chunks)} chunk embedding'e çevriliyor...")
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk["text"])
        sb.table("documents").insert({
            "content": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": embedding
        }).execute()
        if (i+1) % 10 == 0:
            print(f"  ✅ {i+1}/{len(chunks)}")
    print("  ✅ Tamamlandı!")

def index_directory(pdf_dir):
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    print(f"🗂  {len(pdf_files)} PDF bulundu.")
    for f in pdf_files:
        index_pdf(os.path.join(pdf_dir, f))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir")
    parser.add_argument("--file")
    args = parser.parse_args()
    if args.file: index_pdf(args.file)
    elif args.pdf_dir: index_directory(args.pdf_dir)
    else: print("Kullanım: python indexer.py --pdf-dir ./pdfs"); sys.exit(1)
