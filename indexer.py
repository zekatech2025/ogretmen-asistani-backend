"""
PDF İndeksleme Scripti — Gemini Embedding
Kullanım: python indexer.py --pdf-dir ./pdfs
Tek PDF:  python indexer.py --file ./pdfs/belge.pdf
"""
import os
import sys
import argparse
import fitz
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
        task_type="retrieval_document"
    )
    return result["embedding"]


def extract_text(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def chunk_text(pages: list[dict], doc_name: str, chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    chunks = []
    chunk_id = 0
    for page_data in pages:
        words = page_data["text"].split()
        page_num = page_data["page"]
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "document": doc_name,
                        "page": page_num,
                        "chunk": chunk_id
                    }
                })
                chunk_id += 1
            i += chunk_size - overlap
    return chunks


def index_pdf(pdf_path: str):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n📄 İşleniyor: {doc_name}")

    sb.table("documents").delete().eq("metadata->>document", doc_name).execute()

    pages = extract_text(pdf_path)
    if not pages:
        print("  ❌ Metin çıkarılamadı.")
        return

    chunks = chunk_text(pages, doc_name)
    if not chunks:
        print("  ❌ Chunk oluşturulamadı.")
        return

    print(f"  🔄 {len(chunks)} chunk embedding'e çevriliyor...")

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        rows = []
        for chunk in batch:
            embedding = get_embedding(chunk["text"])
            rows.append({
                "content": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": embedding
            })
        sb.table("documents").insert(rows).execute()
        print(f"  ✅ {min(i + batch_size, len(chunks))}/{len(chunks)} chunk eklendi.")

    print(f"  ✅ Tamamlandı!")


def index_directory(pdf_dir: str):
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"❌ {pdf_dir} klasöründe PDF bulunamadı.")
        return
    print(f"🗂  {len(pdf_files)} PDF bulundu.")
    for pdf_file in pdf_files:
        index_pdf(os.path.join(pdf_dir, pdf_file))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", help="PDF klasörü")
    parser.add_argument("--file", help="Tek PDF dosyası")
    args = parser.parse_args()

    if args.file:
        index_pdf(args.file)
    elif args.pdf_dir:
        index_directory(args.pdf_dir)
    else:
        print("Kullanım: python indexer.py --pdf-dir ./pdfs")
        sys.exit(1)
