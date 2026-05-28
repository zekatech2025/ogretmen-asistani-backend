"""
PDF İndeksleme Scripti
Kullanım: python indexer.py --pdf-dir ./pdfs
Yeni PDF için: python indexer.py --file ./pdfs/yeni_belge.pdf
"""
import os
import sys
import argparse
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ChromaDB bağlantısı
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Google embedding fonksiyonu
embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=GEMINI_API_KEY,
    model_name="models/text-embedding-004"
)

collection = client.get_or_create_collection(
    name="meb_mevzuat",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)


def extract_text(pdf_path: str) -> list[dict]:
    """PDF'den metin çıkarır, sayfa bazında döner."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def chunk_text(pages: list[dict], doc_name: str, chunk_size: int = 400, overlap: int = 50) -> list[dict]:
    """
    Metni chunk'lara böler.
    Hukuki/mevzuat metinler için madde başlarından bölmeye çalışır.
    """
    chunks = []
    chunk_id = 0

    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]
        words = text.split()

        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text.strip()) > 50:  # Çok kısa chunk'ları atla
                chunks.append({
                    "id": f"{doc_name}_p{page_num}_c{chunk_id}",
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
    """Tek bir PDF'i indeksler."""
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"📄 İşleniyor: {doc_name}")

    # Daha önce indekslenmiş mi kontrol et
    existing = collection.get(where={"document": doc_name})
    if existing["ids"]:
        print(f"  ⚠️  Zaten indekslenmiş, siliniyor ve yeniden ekleniyor...")
        collection.delete(where={"document": doc_name})

    pages = extract_text(pdf_path)
    if not pages:
        print(f"  ❌ Metin çıkarılamadı: {pdf_path}")
        return

    chunks = chunk_text(pages, doc_name)
    if not chunks:
        print(f"  ❌ Chunk oluşturulamadı: {pdf_path}")
        return

    # Batch olarak ekle (max 100'er)
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch]
        )

    print(f"  ✅ {len(chunks)} chunk eklendi.")


def index_directory(pdf_dir: str):
    """Klasördeki tüm PDF'leri indeksler."""
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"❌ {pdf_dir} klasöründe PDF bulunamadı.")
        return

    print(f"🗂  {len(pdf_files)} PDF bulundu.\n")
    for pdf_file in pdf_files:
        index_pdf(os.path.join(pdf_dir, pdf_file))

    print(f"\n✅ Toplam {collection.count()} chunk veritabanında.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MEB Mevzuat PDF İndeksleyici")
    parser.add_argument("--pdf-dir", help="PDF klasörü")
    parser.add_argument("--file", help="Tek PDF dosyası")
    args = parser.parse_args()

    if args.file:
        index_pdf(args.file)
    elif args.pdf_dir:
        index_directory(args.pdf_dir)
    else:
        print("Kullanım: python indexer.py --pdf-dir ./pdfs")
        print("       veya: python indexer.py --file ./pdfs/belge.pdf")
        sys.exit(1)
