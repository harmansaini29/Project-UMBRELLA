"""
Project UMBRELLA: AST Syntax-Aware Code & Document Chunker
Extracts complete Python classes, functions, docstrings, and Markdown sections
preserving exact line ranges, imports, and metadata for audit-grade citations.
"""

import ast
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rag.models import DocumentChunk, ChunkType

def compute_chunk_hash(file_path: str, start_line: int, end_line: int, content: str) -> str:
    raw = f"{file_path}:{start_line}-{end_line}:{content}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

class AstCodeChunker:
    """Syntax-aware Python code chunker using Python's native AST module."""
    
    @staticmethod
    def extract_imports(tree: ast.AST) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                imports.append(f"from {module} import {names}")
        return imports

    @classmethod
    def chunk_python(cls, file_path: str, code_text: str, repository: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        lines = code_text.splitlines()
        total_lines = len(lines)
        
        if total_lines == 0:
            return chunks

        try:
            tree = ast.parse(code_text, filename=file_path)
        except Exception:
            # Fallback to line-window chunking if AST parsing fails
            return cls.chunk_by_lines(file_path, code_text, repository, ChunkType.CODE)

        module_imports = cls.extract_imports(tree)
        handled_lines = set()

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = getattr(node, 'end_lineno', start)
                symbol_name = f"def {node.name}()"
                content = "\n".join(lines[start - 1 : end])
                docstring = ast.get_docstring(node) or ""
                
                chunk_id = compute_chunk_hash(file_path, start, end, content)
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    file_path=file_path,
                    repository=repository,
                    chunk_type=ChunkType.CODE,
                    symbol_name=symbol_name,
                    start_line=start,
                    end_line=end,
                    content=content,
                    imports=module_imports,
                    metadata={"docstring": docstring, "is_async": isinstance(node, ast.AsyncFunctionDef)}
                ))
                for line_no in range(start, end + 1):
                    handled_lines.add(line_no)

            elif isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, 'end_lineno', start)
                symbol_name = f"class {node.name}"
                content = "\n".join(lines[start - 1 : end])
                docstring = ast.get_docstring(node) or ""
                
                chunk_id = compute_chunk_hash(file_path, start, end, content)
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    file_path=file_path,
                    repository=repository,
                    chunk_type=ChunkType.CODE,
                    symbol_name=symbol_name,
                    start_line=start,
                    end_line=end,
                    content=content,
                    imports=module_imports,
                    metadata={"docstring": docstring, "methods_count": len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])}
                ))
                for line_no in range(start, end + 1):
                    handled_lines.add(line_no)

        # Module-level definitions or configuration
        unhandled = [i for i in range(1, total_lines + 1) if i not in handled_lines]
        if unhandled:
            # Group consecutive unhandled lines (e.g. module config, route definitions)
            start = unhandled[0]
            end = unhandled[-1]
            content = "\n".join(lines[start - 1 : end]).strip()
            if len(content) > 30: # only if meaningful
                chunk_id = compute_chunk_hash(file_path, start, end, content)
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    file_path=file_path,
                    repository=repository,
                    chunk_type=ChunkType.CODE,
                    symbol_name=f"module_level:{Path(file_path).stem}",
                    start_line=start,
                    end_line=end,
                    content=content,
                    imports=module_imports,
                    metadata={"module_level": True}
                ))

        return chunks if chunks else cls.chunk_by_lines(file_path, code_text, repository, ChunkType.CODE)

    @staticmethod
    def chunk_markdown(file_path: str, md_text: str, repository: str) -> List[DocumentChunk]:
        """Header-aware Markdown chunker."""
        chunks: List[DocumentChunk] = []
        lines = md_text.splitlines()
        
        if not lines:
            return chunks

        current_header = Path(file_path).stem
        current_lines: List[str] = []
        start_line = 1

        for idx, line in enumerate(lines, start=1):
            if re.match(r'^#{1,3}\s+', line):
                if current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        end_line = idx - 1
                        chunk_id = compute_chunk_hash(file_path, start_line, end_line, content)
                        chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            file_path=file_path,
                            repository=repository,
                            chunk_type=ChunkType.DOCUMENTATION,
                            symbol_name=current_header,
                            start_line=start_line,
                            end_line=end_line,
                            content=content,
                            imports=[],
                            metadata={"section": current_header}
                        ))
                current_header = line.strip().lstrip('#').strip()
                current_lines = [line]
                start_line = idx
            else:
                current_lines.append(line)

        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                end_line = len(lines)
                chunk_id = compute_chunk_hash(file_path, start_line, end_line, content)
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    file_path=file_path,
                    repository=repository,
                    chunk_type=ChunkType.DOCUMENTATION,
                    symbol_name=current_header,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    imports=[],
                    metadata={"section": current_header}
                ))

        return chunks

    @staticmethod
    def chunk_by_lines(file_path: str, text: str, repository: str, chunk_type: ChunkType, window_size: int = 60, overlap: int = 10) -> List[DocumentChunk]:
        """Generic fallback line-window chunker."""
        chunks: List[DocumentChunk] = []
        lines = text.splitlines()
        total = len(lines)
        if total == 0:
            return chunks

        step = max(1, window_size - overlap)
        for start_idx in range(0, total, step):
            end_idx = min(start_idx + window_size, total)
            content = "\n".join(lines[start_idx:end_idx]).strip()
            if not content:
                continue
            start_line = start_idx + 1
            end_line = end_idx
            chunk_id = compute_chunk_hash(file_path, start_line, end_line, content)
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                file_path=file_path,
                repository=repository,
                chunk_type=chunk_type,
                symbol_name=f"block:{start_line}-{end_line}",
                start_line=start_line,
                end_line=end_line,
                content=content,
                imports=[],
                metadata={}
            ))
            if end_idx >= total:
                break

        return chunks

def chunk_file(file_path: Path, relative_to: Path, repository: str) -> List[DocumentChunk]:
    """Auto-detects file type and runs appropriate syntax-aware chunker."""
    rel_path_str = str(file_path.relative_to(relative_to)).replace("\\", "/")
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    ext = file_path.suffix.lower()
    if ext == ".py":
        return AstCodeChunker.chunk_python(rel_path_str, content, repository)
    elif ext in [".md", ".txt"]:
        return AstCodeChunker.chunk_markdown(rel_path_str, content, repository)
    elif ext in [".json", ".yaml", ".yml", ".sql"]:
        return AstCodeChunker.chunk_by_lines(rel_path_str, content, repository, ChunkType.CONFIG)
    else:
        return []
