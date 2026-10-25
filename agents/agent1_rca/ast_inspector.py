"""
Agent 1 Component: AST & Stack Trace Inspector
Extracts syntactic AST nodes, failing lines, and symbol scopes from runtime tracebacks.
"""

import ast
import os
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class StackFrameInfo(BaseModel):
    file_path: str
    line_number: int
    function_name: str
    code_context: Optional[str] = None


class ASTDiagnosis(BaseModel):
    has_source_code: bool = False
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    enclosing_symbol: Optional[str] = None
    ast_node_type: Optional[str] = None
    extracted_parameters: Dict[str, Any] = Field(default_factory=dict)
    code_snippet: Optional[str] = None
    syntax_valid: bool = True


class ASTInspector:
    """Inspects Python source code and tracebacks using Python AST."""

    @staticmethod
    def parse_stack_trace(traceback_str: str) -> List[StackFrameInfo]:
        """Parses a standard Python traceback into structured frames."""
        frames: List[StackFrameInfo] = []
        if not traceback_str:
            return frames

        # Regex for File "path", line X, in function
        pattern = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')
        lines = traceback_str.splitlines()

        for i, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                f_path, l_num, func = match.groups()
                code_ctx = None
                if i + 1 < len(lines):
                    code_ctx = lines[i + 1].strip()
                frames.append(StackFrameInfo(
                    file_path=f_path,
                    line_number=int(l_num),
                    function_name=func,
                    code_context=code_ctx
                ))

        return frames

    @classmethod
    def inspect_file_at_line(cls, file_path: str, line_number: int) -> ASTDiagnosis:
        """Inspects source file at a given line number using AST parsing."""
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            return ASTDiagnosis(has_source_code=False, file_path=file_path, line_number=line_number)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            # AST parse
            tree = ast.parse(content, filename=file_path)

            # Find enclosing function/class
            enclosing = None
            node_type = None
            extracted_params: Dict[str, Any] = {}

            for node in ast.walk(tree):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    if node.lineno <= line_number <= (node.end_lineno or node.lineno):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            enclosing = f"def {node.name}()"
                        elif isinstance(node, ast.ClassDef):
                            enclosing = f"class {node.name}"
                        elif isinstance(node, ast.Assign):
                            node_type = "Assignment"
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    val = cls._get_literal_value(node.value)
                                    extracted_params[target.id] = val
                        elif isinstance(node, ast.Call):
                            node_type = f"Call({getattr(node.func, 'id', getattr(node.func, 'attr', 'func'))})"
                            for kw in node.keywords:
                                extracted_params[kw.arg] = cls._get_literal_value(kw.value)

            # Extract window of code snippet (line - 3 to line + 3)
            start_idx = max(0, line_number - 4)
            end_idx = min(len(lines), line_number + 3)
            snippet = "\n".join(lines[start_idx:end_idx])

            return ASTDiagnosis(
                has_source_code=True,
                file_path=file_path,
                line_number=line_number,
                enclosing_symbol=enclosing or "module-level",
                ast_node_type=node_type or "Statement",
                extracted_parameters=extracted_params,
                code_snippet=snippet,
                syntax_valid=True
            )

        except SyntaxError:
            return ASTDiagnosis(
                has_source_code=True,
                file_path=file_path,
                line_number=line_number,
                syntax_valid=False
            )
        except Exception as err:
            return ASTDiagnosis(
                has_source_code=False,
                file_path=file_path,
                line_number=line_number,
                code_snippet=f"Inspection error: {err}"
            )

    @classmethod
    def _get_literal_value(cls, node: ast.AST) -> Any:
        """Safely extracts a literal scalar value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Call):
            # Handle int(...), float(...), str(...)
            if isinstance(node.func, ast.Name) and node.func.id in ("int", "float", "str"):
                if node.args:
                    inner_val = cls._get_literal_value(node.args[0])
                    try:
                        if node.func.id == "int":
                            return int(inner_val)
                        elif node.func.id == "float":
                            return float(inner_val)
                        elif node.func.id == "str":
                            return str(inner_val)
                    except (ValueError, TypeError):
                        pass
            # Handle os.environ.get("VAR", "default_val")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if len(node.args) >= 2:
                    return cls._get_literal_value(node.args[1])
        elif isinstance(node, ast.Name):
            return node.id
        return "<expr>"
