#!/usr/bin/env python3
"""Add explicit exception chaining (from e / from None) for B904 fixes."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = (
    ROOT / "src",
    ROOT / "web-sota" / "backend",
    ROOT / "tests",
)
SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".venv",
        "fresh_venv",
        "site-packages",
        "node_modules",
    }
)


class B904Collector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.except_stack: list[str | None] = []
        self.fixes: list[tuple[ast.Raise, str]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.except_stack.append(node.name)
        self.generic_visit(node)
        self.except_stack.pop()

    def visit_Raise(self, node: ast.Raise) -> None:
        if self.except_stack and node.exc is not None and node.cause is None:
            alias = self.except_stack[-1]
            from_expr = alias if alias is not None else "None"
            self.fixes.append((node, from_expr))
        self.generic_visit(node)


def apply_fixes(source: str, fixes: list[tuple[ast.Raise, str]]) -> str:
    if not fixes:
        return source
    lines = source.splitlines(keepends=True)
    ordered = sorted(
        fixes,
        key=lambda item: (
            item[0].end_lineno or item[0].lineno,
            item[0].end_col_offset or 0,
        ),
        reverse=True,
    )
    for node, from_expr in ordered:
        end_line = (node.end_lineno or node.lineno) - 1
        end_col = node.end_col_offset
        if end_col is None:
            continue
        line = lines[end_line]
        lines[end_line] = line[:end_col] + f" from {from_expr}" + line[end_col:]
    return "".join(lines)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def process_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        print(f"SKIP (syntax error): {path}: {exc}", file=sys.stderr)
        return 0
    collector = B904Collector()
    collector.visit(tree)
    if not collector.fixes:
        return 0
    updated = apply_fixes(text, collector.fixes)
    if updated != text:
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
    return len(collector.fixes)


def iter_py_files() -> list[Path]:
    files: list[Path] = []
    for base in SCAN_DIRS:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if not should_skip(path):
                files.append(path)
    return files


def main() -> int:
    total = 0
    changed_files = 0
    for path in iter_py_files():
        count = process_file(path)
        if count:
            changed_files += 1
            total += count
            print(f"{path.relative_to(ROOT)}: {count} fix(es)")
    print(f"Done: {total} raise(s) updated in {changed_files} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
