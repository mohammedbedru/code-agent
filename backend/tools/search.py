from pathlib import Path
from .filesystem import IGNORED_DIRS, SEARCHABLE_EXTENSIONS


def search_code(workspace: str, query: str, context_lines: int = 3) -> str:
    root = Path(workspace)
    if not root.exists():
        return f"ERROR: Directory does not exist: {workspace}"

    query = query.strip()
    if not query:
        return "ERROR: Search query is empty."

    terms = [t.strip().lower() for t in query.split("|") if t.strip()]
    if not terms:
        return "ERROR: No valid search terms."

    results = []

    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in SEARCHABLE_EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.splitlines()
        matched = [
            i + 1 for i, line in enumerate(lines)
            if any(t in line.lower() for t in terms)
        ]

        if not matched:
            continue

        included = set()
        for ln in matched:
            for n in range(max(1, ln - context_lines), min(len(lines), ln + context_lines) + 1):
                included.add(n)

        rel = path.relative_to(root)
        results.append(f"\n{rel}\n" + "-" * len(str(rel)))

        prev = None
        for ln in sorted(included):
            if prev is not None and ln > prev + 1:
                results.append("...")
            marker = ">>>" if ln in matched else "   "
            results.append(f"{marker} {ln}: {lines[ln - 1]}")
            prev = ln

    if not results:
        return f"NO_MATCHES_FOUND\n\nQuery '{query}' not found in workspace."

    return "\n".join(results)
