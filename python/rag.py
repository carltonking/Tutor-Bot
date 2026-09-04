import re
from pathlib import Path
from pypdf import PdfReader

CHUNK_SIZE = 512
OVERLAP = 64

def extract_text(path: str) -> tuple[str, int]:
    """Extract text + page count. Dispatches by extension: PDFs via pypdf,
    text/markdown/code files read directly (pages=1)."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        pages = len(reader.pages)
        texts = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            texts.append(t)
        return "\n".join(texts), pages
    # plain text-ish files: .txt .md .markdown .csv and any unknown text extension
    try:
        return p.read_text(encoding="utf-8", errors="replace"), 1
    except Exception as e:
        raise ValueError(f"Unsupported file type: {p.suffix or '(none)'}") from e

def chunk_text(text: str, size=CHUNK_SIZE, overlap=OVERLAP):
    tokens = re.findall(r"\S+", text)  # naive token = word
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = " ".join(tokens[i:i+size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
        if i <= 0:
            break
    return chunks

import hashlib, math
def embed_text(text: str, dim=384):
    # deterministic hash-based embedding stub (replaces nomic until Ollama/Zen embeddings land)
    # stable, no API needed
    h = hashlib.sha256(text.encode()).digest()
    # expand to dim via repeated hashing
    vec = []
    for i in range(dim):
        b = h[i % len(h)]
        vec.append((b / 255.0) * 2 - 1)  # -1..1
        # mix
        h = hashlib.sha256(h + i.to_bytes(2,'little')).digest()
    # normalize
    n = math.sqrt(sum(x*x for x in vec)) or 1
    return [x/n for x in vec]

def cosine(a,b):
    return sum(x*y for x,y in zip(a,b))

# Try Ollama nomic-embed-text if available, fallback to hash
def embed_via_ollama(text: str):
    try:
        import httpx
        r = httpx.post("http://localhost:11434/api/embed", json={"model":"nomic-embed-text","input": text}, timeout=5)
        if r.status_code==200:
            j=r.json()
            # Ollama returns {"embeddings": [[...]]}
            emb = j.get("embeddings", [[]])[0]
            if emb:
                import math
                n = math.sqrt(sum(x*x for x in emb)) or 1
                return [x/n for x in emb]
    except: pass
    return None

def embed_text_smart(text: str):
    return embed_via_ollama(text) or embed_text(text)
