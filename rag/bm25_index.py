"""
Project UMBRELLA: Code-Aware BM25 Lexical Index
Implements Okapi BM25 with syntax-aware tokenization (camelCase & snake_case splitting)
for exact code token, exception message, route path, and config key retrieval.
"""

import math
import pickle
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rag.models import DocumentChunk, ChunkType

def tokenize_code(text: str) -> List[str]:
    """Tokenizes code by handling camelCase, snake_case, identifiers, and symbols."""
    # Split camelCase: handleDbError -> handle Db Error
    text_camel = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Split non-alphanumeric except underscores and dots
    tokens_raw = re.split(r'[^a-zA-Z0-9_\.]+', text_camel.lower())
    
    tokens: List[str] = []
    for tok in tokens_raw:
        if not tok:
            continue
        tokens.append(tok)
        # Also split snake_case components
        if "_" in tok:
            for sub in tok.split("_"):
                if sub:
                    tokens.append(sub)
        # Also split dotted paths
        if "." in tok:
            for sub in tok.split("."):
                if sub:
                    tokens.append(sub)
    return tokens

class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[DocumentChunk] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.doc_count: int = 0
        self.inverted_index: Dict[str, Dict[int, int]] = {} # token -> {doc_idx: freq}
        self.idf: Dict[str, float] = {}

    def fit(self, chunks: List[DocumentChunk]):
        """Builds BM25 inverted index and calculates IDF over document chunks."""
        self.chunks = chunks
        self.doc_count = len(chunks)
        self.doc_lengths = []
        self.inverted_index = {}
        total_tokens = 0

        for doc_idx, chunk in enumerate(chunks):
            # Include symbol_name and content for lexical scoring
            full_text = f"{chunk.symbol_name or ''} {chunk.content}"
            tokens = tokenize_code(full_text)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_tokens += doc_len

            term_freqs: Dict[str, int] = {}
            for tok in tokens:
                term_freqs[tok] = term_freqs.get(tok, 0) + 1

            for tok, freq in term_freqs.items():
                if tok not in self.inverted_index:
                    self.inverted_index[tok] = {}
                self.inverted_index[tok][doc_idx] = freq

        self.avg_doc_length = total_tokens / max(1, self.doc_count)

        # Precompute IDF
        self.idf = {}
        for tok, posting in self.inverted_index.items():
            doc_freq = len(posting)
            # Okapi BM25 IDF formula
            self.idf[tok] = math.log(1.0 + (self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5))

    def search(self, query: str, top_k: int = 10, filter_repo: Optional[str] = None, filter_type: Optional[ChunkType] = None) -> List[Tuple[DocumentChunk, float, int]]:
        """Returns list of (DocumentChunk, bm25_score, rank)."""
        tokens = tokenize_code(query)
        scores: Dict[int, float] = {}

        for tok in tokens:
            if tok not in self.inverted_index:
                continue
            tok_idf = self.idf[tok]
            posting = self.inverted_index[tok]
            for doc_idx, freq in posting.items():
                chunk = self.chunks[doc_idx]
                if filter_repo and chunk.repository != filter_repo:
                    continue
                if filter_type and chunk.chunk_type != filter_type:
                    continue

                doc_len = self.doc_lengths[doc_idx]
                denom = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                score = tok_idf * (freq * (self.k1 + 1.0)) / max(1e-6, denom)
                scores[doc_idx] = scores.get(doc_idx, 0.0) + score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[doc_idx], score, rank + 1) for rank, (doc_idx, score) in enumerate(ranked)]

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: Path) -> "BM25Index":
        with open(filepath, 'rb') as f:
            return pickle.load(f)
