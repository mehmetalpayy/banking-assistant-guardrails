import os
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_markdown_files(directory: str) -> List[str]:
    chunks = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".md"):
            continue
        file_path = os.path.join(directory, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        title = os.path.splitext(filename)[0]
        current_h1 = ""
        current_h2 = ""
        current_content: List[str] = []
        for line in lines:
            if line.startswith("# "):
                if current_content:
                    chunks.append(format_chunk(title, current_h1, current_h2, current_content))
                current_h1 = line[2:].strip()
                current_h2 = ""
                current_content = []
            elif line.startswith("## "):
                if current_content:
                    chunks.append(format_chunk(title, current_h1, current_h2, current_content))
                current_h2 = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        if current_content:
            chunks.append(format_chunk(title, current_h1, current_h2, current_content))
    return chunks


def format_chunk(title: str, h1: str, h2: str, content: List[str]) -> str:
    section = f"{h1}/{h2}" if h2 else h1
    body = "\n".join(content).strip()
    return f"Title: {title}\nSection: {section}\n{body}"


class SimpleVectorDB:
    def __init__(self) -> None:
        self.embeddings: List[np.ndarray] = []
        self.strings: List[str] = []

    def add_strings(self, strings: List[str]) -> None:
        new_embeddings = EMBEDDING_MODEL.encode(strings)
        self.embeddings.extend(new_embeddings)
        self.strings.extend(strings)

    def query(self, query: str, k: int = 3, threshold: float = 0.9) -> List[Tuple[str, float]]:
        if not self.embeddings:
            return []
        query_emb = EMBEDDING_MODEL.encode([query])[0]
        emb_array = np.array(self.embeddings)
        similarities = np.dot(emb_array, query_emb) / (
            np.linalg.norm(emb_array, axis=1) * np.linalg.norm(query_emb)
        )
        distances = 1 - similarities
        sorted_indices = np.argsort(distances)
        results = []
        for idx in sorted_indices:
            if distances[idx] < threshold and len(results) < k:
                results.append((self.strings[idx], float(distances[idx])))
            else:
                break
        results.reverse()
        return results

    def format_context(self, results: List[Tuple[str, float]]) -> str:
        if not results:
            return ""
        parts = []
        for i, (text, _) in enumerate(results, 1):
            parts.append(f"# Context {i}:\n{text}")
        return "\n\n".join(parts)

    @classmethod
    def from_files(cls, directory: str) -> "SimpleVectorDB":
        chunks = chunk_markdown_files(directory)
        db = cls()
        db.add_strings(chunks)
        return db
