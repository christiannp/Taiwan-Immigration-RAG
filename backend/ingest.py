import os, hashlib, sqlite3, time, random
from playwright.sync_api import sync_playwright
from qdrant_client import QdrantClient, models
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
import PyPDF2

# Initialize Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
client = genai.GenerativeModel("text-embedding-004")

# Set up Qdrant client (pointing to QDRANT_URL)
qdrant = QdrantClient(url=os.getenv("QDRANT_URL"))

# Ensure Qdrant collection exists
if "immigration" not in [col.name for col in qdrant.get_collections().collections]:
    qdrant.recreate_collection(
        collection_name="immigration",
        vector_size=768,
        distance=models.Distance.COSINE
    )

# SQLite for tracking processed URLs
conn = sqlite3.connect("ingest.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS docs (
    url TEXT PRIMARY KEY,
    hash TEXT,
    updated TIMESTAMP
)""")
conn.commit()

# List of User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 ...",  # (Add a few valid UA strings)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
]

def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def process_url(url: str):
    # Check if URL has changed since last time
    res = cursor.execute("SELECT hash FROM docs WHERE url=?", (url,)).fetchone()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=random.choice(USER_AGENTS))
        page.goto(url)
        # If PDF, use PyPDF2 (assumes direct link to PDF)
        if url.lower().endswith(".pdf"):
            pdf_bytes = page.content().encode()
            sha = hash_content(pdf_bytes)
            if res and res[0] == sha: 
                return  # no change
            text = ""
            reader = PyPDF2.PdfReader(pdf_bytes)
            for pg in reader.pages:
                text += pg.extract_text() + "\n"
        else:
            html = page.content().encode()
            sha = hash_content(html)
            if res and res[0] == sha:
                return  # no change
            text = page.inner_text("body")
        # Update SQLite
        cursor.execute("REPLACE INTO docs (url,hash,updated) VALUES (?,?,?)", (url, sha, int(time.time())))
        conn.commit()
        browser.close()
    # Chunking with context (title/header)
    title = "Document Title"  # placeholder; parse actual title if needed
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    chunks = splitter.split_text(text)
    payloads = []
    for i, chunk in enumerate(chunks):
        content_with_ctx = f"{title} - Section {i+1}: {chunk}"
        embedding = client.predict(content_with_ctx)
        payloads.append(models.PointStruct(
            id=f"{url}#{i}",
            vector=embedding.prediction,
            payload={"url": url, "title": title, "section": f"Section {i+1}", "text": chunk}
        ))
    # Upsert to Qdrant
    qdrant.upsert(collection_name="immigration", points=payloads)

# Example: scrape specific pages (would be more dynamic in real scraper)
urls_to_scrape = [
    "https://www.immigration.gov.tw/5475/5478/141465/141808/141824/",  # example page
    # Add more URLs or PDF links...
]

for url in urls_to_scrape:
    process_url(url)