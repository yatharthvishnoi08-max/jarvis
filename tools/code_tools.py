"""Safe mathematical evaluation, AST-validated Python code execution, and unified patching.
Inspired by OpenJarvis code execution and diff-patching capabilities.
"""
from __future__ import annotations

import ast
import math
import operator
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------- CALCULATOR -----------------

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MATH_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
}

def _eval_ast(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Disallowed constant type: {type(node.value).__name__}")
    if isinstance(node, ast.BinOp):
        op_fn = _BINOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Pow) and right > 1000:
            raise ValueError("Exponent too large (limit: 1000).")
        return op_fn(left, right)
    if isinstance(node, ast.UnaryOp):
        op_fn = _UNARYOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_fn(_eval_ast(node.operand))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _MATH_FUNCS:
            fn = _MATH_FUNCS[node.func.id]
            args = [_eval_ast(arg) for arg in node.args]
            return fn(*args)
        raise ValueError("Only standard math functions are permitted.")
    if isinstance(node, ast.Name):
        if node.id in _MATH_FUNCS:
            return _MATH_FUNCS[node.id]
        raise ValueError(f"Unknown variable: {node.id}")
    raise ValueError(f"Disallowed expression node: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Safely evaluate mathematical formulas using Python's AST parser without eval().
    Supports +, -, *, /, //, %, **, sqrt, log, sin, cos, tan, pi, e, etc.
    """
    expr = expression.strip()
    if not expr:
        return "Expression cannot be empty."
    try:
        parsed = ast.parse(expr, mode="eval")
        result = _eval_ast(parsed)
        return str(result)
    except Exception as e:
        return f"Math Evaluation Error: {str(e)}"


# ----------------- CODE INTERPRETER -----------------

_ALLOWED_IMPORTS = frozenset({"json", "math", "time", "re", "datetime", "random", "collections", "itertools"})
_BLOCKED_NAMES = frozenset({
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "globals", "locals", "vars", "getattr", "setattr", "delattr", "memoryview"
})

def _validate_python_ast(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax Error: {e.msg} at line {e.lineno}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg not in _ALLOWED_IMPORTS:
                    return f"Security Restriction: Import of '{root_pkg}' is forbidden. Allowed: {sorted(list(_ALLOWED_IMPORTS))}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg not in _ALLOWED_IMPORTS:
                    return f"Security Restriction: Import from '{root_pkg}' is forbidden."
        elif isinstance(node, ast.Name):
            if node.id in _BLOCKED_NAMES:
                return f"Security Restriction: Usage of '{node.id}' is blocked."
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return "Security Restriction: Dunder attribute access is forbidden."
    return None


def code_interpreter(code: str, timeout: int = 10) -> str:
    """Execute Python code in a secured, isolated subprocess with AST safety validation.
    Captures stdout, stderr, and execution exceptions.
    """
    code = code.strip()
    if not code:
        return "No code provided to execute."

    validation_err = _validate_python_ast(code)
    if validation_err:
        return validation_err

    # Create temporary script file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        temp_path = f.name

    try:
        # Run isolated with -I (isolated mode: ignore env, no site-packages injection)
        proc = subprocess.run(
            [sys.executable, "-I", temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        
        output_parts = []
        if stdout:
            output_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")
        if not stdout and not stderr:
            output_parts.append(f"Process completed with exit code {proc.returncode} (No output)")
            
        return "\n\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return f"Execution Error: Code timed out after {timeout} seconds."
    except Exception as e:
        return f"Execution Error: {str(e)}"
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


# ----------------- UNIFIED DIFF PATCH APPLIER -----------------

def apply_unified_patch(patch_text: str) -> str:
    """Apply a unified diff patch string to a target file.
    Follows standard git/diff hunk headers (@@ -start,count +start,count @@).
    """
    patch_lines = patch_text.splitlines()
    target_file = None

    for line in patch_lines:
        if line.startswith("+++ "):
            # Format: +++ b/path/to/file or +++ path/to/file
            path_part = line[4:].strip().split("\t")[0]
            if path_part.startswith("b/"):
                path_part = path_part[2:]
            target_file = path_part
            break

    if not target_file:
        return "Error: Could not determine target file from '+++ ' header in patch."

    path = Path(target_file).resolve()
    if not path.exists():
        return f"Error: Target file does not exist: {path}"

    try:
        content = path.read_text(encoding="utf-8")
        file_lines = content.splitlines(keepends=True)
    except Exception as e:
        return f"Error reading file '{target_file}': {str(e)}"

    # Very robust patch application: write patch to temp file and use git apply if available
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as pf:
        pf.write(patch_text + "\n")
        patch_file = pf.name

    try:
        res = subprocess.run(
            ["git", "apply", "--unidiff-zero", patch_file],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            return f"SUCCESS: Unified patch applied cleanly to '{target_file}'."
        else:
            return f"git apply failed: {res.stderr.strip()}"
    except Exception as e:
        return f"Patch Application Error: {str(e)}"
    finally:
        try:
            os.remove(patch_file)
        except OSError:
            pass
