"""
Project UMBRELLA: Dense Vector Index powered by FAISS
Provides fast semantic vector retrieval over code and runbook descriptions,
supporting local TF-IDF dense projection and pluggable neural embedding adapters.
"""

import pickle
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from rag.models import DocumentChunk, ChunkType

class VectorIndex:
    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.faiss_index: Optional[faiss.IndexFlatIP] = None

    def fit(self, chunks: List[DocumentChunk]):
        """Generates embeddings and populates the FAISS Inner Product index."""
        self.chunks = chunks
        if not chunks:
            return

        corpus = [f"{c.symbol_name or ''} {c.content}" for c in chunks]
        
        # We use a sublinear TF-IDF vectorizer projected to dimension features
        self.vectorizer = TfidfVectorizer(
            max_features=self.dimension,
            sublinear_tf=True,
            stop_words='english',
            ngram_range=(1, 2)
        )
        matrix = self.vectorizer.fit_transform(corpus).toarray().astype('float32')
        
        # Ensure matrix has exact dimension
        if matrix.shape[1] < self.dimension:
            pad = np.zeros((matrix.shape[0], self.dimension - matrix.shape[1]), dtype='float32')
            matrix = np.hstack([matrix, pad])

        # Normalize to unit length for cosine similarity
        faiss.normalize_L2(matrix)
        
        # Create FAISS IndexFlatIP (Inner Product = Cosine Similarity for normalized vectors)
        self.faiss_index = faiss.IndexFlatIP(self.dimension)
        self.faiss_index.add(matrix)

    def search(self, query: str, top_k: int = 10, filter_repo: Optional[str] = None, filter_type: Optional[ChunkType] = None) -> List[Tuple[DocumentChunk, float, int]]:
        """Searches FAISS vector space and returns list of (DocumentChunk, cosine_similarity, rank)."""
        if not self.faiss_index or not self.vectorizer or not self.chunks:
            return []

        q_vec = self.vectorizer.transform([query]).toarray().astype('float32')
        if q_vec.shape[1] < self.dimension:
            pad = np.zeros((1, self.dimension - q_vec.shape[1]), dtype='float32')
            q_vec = np.hstack([q_vec, pad])
            
        faiss.normalize_L2(q_vec)
        
        # Retrieve candidate pool
        candidate_k = min(len(self.chunks), top_k * 4)
        scores, indices = self.faiss_index.search(q_vec, candidate_k)
        
        results: List[Tuple[DocumentChunk, float, int]] = []
        rank = 1
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx]
            if filter_repo and chunk.repository != filter_repo:
                continue
            if filter_type and chunk.chunk_type != filter_type:
                continue
            
            results.append((chunk, float(score), rank))
            rank += 1
            if len(results) >= top_k:
                break
                
        return results

    def save(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        # Save FAISS index
        faiss.write_index(self.faiss_index, str(directory / "vector_index.faiss"))
        # Save metadata and vectorizer
        meta = {
            "dimension": self.dimension,
            "chunks": self.chunks,
            "vectorizer": self.vectorizer
        }
        with open(directory / "vector_meta.pkl", 'wb') as f:
            pickle.dump(meta, f)

    @classmethod
    def load(cls, directory: Path) -> "VectorIndex":
        instance = cls()
        instance.faiss_index = faiss.read_index(str(directory / "vector_index.faiss"))
        with open(directory / "vector_meta.pkl", 'rb') as f:
            meta = pickle.load(f)
            instance.dimension = meta["dimension"]
            instance.chunks = meta["chunks"]
            instance.vectorizer = meta["vectorizer"]
        return instance
