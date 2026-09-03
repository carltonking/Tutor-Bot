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
