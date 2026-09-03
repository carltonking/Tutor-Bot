import re
from pathlib import Path
from pypdf import PdfReader

CHUNK_SIZE = 512
OVERLAP = 64

def extract_text(path: str) -> tuple[str, int]:
    reader = PdfReader(path)
    pages = len(reader.pages)
    texts = []
    for p in reader.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        texts.append(t)
    return "\n".join(texts), pages

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
