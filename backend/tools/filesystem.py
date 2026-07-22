from pathlib import Path

IGNORED_DIRS = {
    ".git", ".venv", "venv", "myenv", "env",
    "node_modules", "__pycache__", ".next", "dist", "build", ".idea", ".vs",
}

SEARCHABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".php", ".go", ".rs",
    ".c", ".cpp", ".h", ".cs", ".json", ".yaml", ".yml", ".xml", ".sql",
    ".md", ".txt", ".env", ".toml", ".sh", ".bat", ".html", ".css",
}


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def _resolve_path(workspace: str, file_path: str) -> Path:
    workspace_root = Path(workspace).resolve()
    target = (workspace_root / file_path).resolve()
    if not str(target).startswith(str(workspace_root)):
        raise ValueError(f"Path escapes workspace: {file_path}")
    return target


def list_files(workspace: str) -> str:
    root = Path(workspace)
    if not root.exists():
        return f"ERROR: Directory does not exist: {workspace}"
    files = sorted(
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and not _is_ignored(p)
    )
    return "\n".join(files) if files else "No files found."


def read_file(workspace: str, file_path: str, start_line: int = None, end_line: int = None) -> str:
    try:
        path = _resolve_path(workspace, file_path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not path.exists():
        return f"ERROR: File does not exist: {file_path}"
    if not path.is_file():
        return f"ERROR: Not a file: {file_path}"

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"ERROR reading file: {e}"

    lines = content.splitlines()
    total = len(lines)

    if start_line is None and end_line is None:
        numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
        return f"[{file_path}] ({total} lines)\n{numbered}"

    s = max(1, start_line or 1)
    e = min(total, end_line or total)
    selected = lines[s - 1:e]
    numbered = "\n".join(f"{s+i}: {l}" for i, l in enumerate(selected))
    return f"[{file_path}] lines {s}-{e}\n{numbered}"


def create_file(workspace: str, file_path: str, content: str) -> str:
    try:
        path = _resolve_path(workspace, file_path)
    except ValueError as e:
        return f"ERROR: {e}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Created: {file_path}"


def edit_file(workspace: str, file_path: str, old_text: str, new_text: str) -> str:
    try:
        path = _resolve_path(workspace, file_path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not path.exists():
        return f"ERROR: File does not exist: {file_path}"

    content = path.read_text(encoding="utf-8", errors="ignore")

    count = content.count(old_text)
    if count == 0:
        return f"ERROR: old_text not found in {file_path}. Verify the exact text and try again."
    if count > 1:
        return f"ERROR: old_text found {count} times in {file_path}. Make old_text more specific."

    new_content = content.replace(old_text, new_text, 1)
    path.write_text(new_content, encoding="utf-8")
    return f"Edited: {file_path}"


def delete_file(workspace: str, file_path: str) -> str:
    try:
        path = _resolve_path(workspace, file_path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not path.exists():
        return f"ERROR: File does not exist: {file_path}"

    path.unlink()
    return f"Deleted: {file_path}"


def get_file_info(workspace: str, file_path: str) -> str:
    try:
        path = _resolve_path(workspace, file_path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not path.exists():
        return f"ERROR: File does not exist: {file_path}"

    stat = path.stat()
    lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return (
        f"path: {file_path}\n"
        f"size: {stat.st_size} bytes\n"
        f"lines: {lines}\n"
        f"extension: {path.suffix}"
    )
