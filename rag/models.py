"""
Project UMBRELLA: Central Hybrid Agentic RAG Data Contracts
Defines typed Pydantic models for AST code chunks, queries, citations, and search results.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ChunkType(str, Enum):
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    TEST = "test"

class DocumentChunk(BaseModel):
    chunk_id: str = Field(..., description="Deterministic hash uniquely identifying this chunk")
    file_path: str = Field(..., description="Relative file path within repository")
    repository: str = Field(..., description="Origin repository name")
    chunk_type: ChunkType = Field(default=ChunkType.CODE, description="Type of content")
    symbol_name: Optional[str] = Field(default=None, description="Class, function, or section title")
    start_line: int = Field(default=1, description="1-indexed starting line")
    end_line: int = Field(default=1, description="1-indexed ending line")
    content: str = Field(..., description="Raw text or source code of chunk")
    imports: List[str] = Field(default_factory=list, description="Imports or dependency references")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags and filters")

class Citation(BaseModel):
    file_path: str
    repository: str
    symbol_name: Optional[str] = None
    start_line: int
    end_line: int
    commit_sha: Optional[str] = None

class SearchQuery(BaseModel):
    query_text: str = Field(..., description="Symptom, error trace, API path, or natural language query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to retrieve")
    filter_repository: Optional[str] = Field(default=None, description="Optional repository name filter")
    filter_type: Optional[ChunkType] = Field(default=None, description="Optional chunk type filter")
    bm25_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Relative weight for lexical BM25")
    vector_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Relative weight for dense vector")

class RetrievalResult(BaseModel):
    chunk: DocumentChunk
    rrf_score: float = Field(..., description="Reciprocal Rank Fusion score")
    bm25_rank: Optional[int] = Field(default=None, description="Rank from BM25 (1-indexed)")
    vector_rank: Optional[int] = Field(default=None, description="Rank from Vector Search (1-indexed)")
    citation: Citation
