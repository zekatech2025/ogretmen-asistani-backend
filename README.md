# Backend Kurulum Rehberi

## 1. Supabase'de Tabloları Oluşturun

Supabase paneli → SQL Editor → `supabase_setup.sql` içeriğini yapıştırın → Run

---

## 2. Supabase Service Key Alın

Supabase paneli → Settings → API → **service_role** anahtarını kopyalayın
(anon key değil, service_role key)

---

## 3. Gemini API Key Alın

https://aistudio.google.com/apikey → Create API Key

---

## 4. Projeyi Bilgisayarınıza Kurun

```bash
# Klasöre girin
cd backend

# Sanal ortam oluşturun
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# .env dosyası oluşturun
cp .env.example .env
```

`.env` dosyasını açın, değerleri doldurun:
```
GEMINI_API_KEY=...
SUPABASE_URL=https://kwbabrfnlgojorpxyjdy.supabase.co
SUPABASE_SERVICE_KEY=...
```

---

## 5. PDF'leri İndeksleyin

```bash
# pdfs klasörü oluşturun
mkdir pdfs

# PDF'lerinizi pdfs/ klasörüne koyun
# Sonra indeksleyin:
python indexer.py --pdf-dir ./pdfs
```

---

## 6. Lokal Test

```bash
python main.py
# http://localhost:8000 adresinde çalışır
# http://localhost:8000/docs adresinde Swagger UI açılır
```

---

## 7. Railway'e Deploy

```bash
# Railway CLI yükleyin
npm install -g @railway/cli

# Giriş yapın
railway login

# Proje oluşturun
railway init

# Deploy edin
railway up
```

Railway panelinde → Variables bölümüne şunları ekleyin:
```
GEMINI_API_KEY=...
SUPABASE_URL=https://kwbabrfnlgojorpxyjdy.supabase.co
SUPABASE_SERVICE_KEY=...
ALLOWED_ORIGINS=https://frabjous-shortbread-27b247.netlify.app
CHROMA_PATH=./chroma_db
MAX_PROMPTS_PER_USER=1000
```

Deploy tamamlandığında Railway size bir URL verir:
`https://backend-production-xxxx.up.railway.app`

---

## 8. Web ve Flutter'ı Güncelleyin

Backend URL'nizi alın ve bildirin — web ile Flutter'daki API bağlantılarını güncelleyeceğiz.

---

## Klasör Yapısı

```
backend/
├── main.py              → FastAPI uygulaması
├── rag.py               → RAG motoru
├── indexer.py           → PDF indeksleme
├── requirements.txt     → Python bağımlılıkları
├── Procfile             → Railway başlatma komutu
├── railway.json         → Railway yapılandırması
├── supabase_setup.sql   → Supabase tablo kurulumu
├── .env.example         → Ortam değişkenleri şablonu
└── pdfs/                → PDF belgelerinizi buraya koyun
```
