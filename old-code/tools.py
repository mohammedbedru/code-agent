# from pathlib import Path


# IGNORED_DIRECTORIES = {
#     ".git",
#     ".venv",
#     "venv",
#     "myenv",
#     "env",
#     "node_modules",
#     "__pycache__",
# }


# SEARCHABLE_EXTENSIONS = {
#     ".py",
#     ".js",
#     ".ts",
#     ".tsx",
#     ".jsx",
#     ".java",
#     ".php",
#     ".go",
#     ".rs",
#     ".c",
#     ".cpp",
#     ".h",
#     ".cs",
#     ".json",
#     ".yaml",
#     ".yml",
#     ".xml",
#     ".sql",
#     ".md",
#     ".txt",
#     ".env",
# }


# def is_ignored(path: Path):
#     return any(
#         part in IGNORED_DIRECTORIES
#         for part in path.parts
#     )


# def list_files(directory: str) -> str:
#     """
#     List all relevant files in a project directory.
#     """

#     root = Path(directory)

#     if not root.exists():
#         return f"ERROR: Directory does not exist: {directory}"

#     files = []

#     for path in root.rglob("*"):

#         if is_ignored(path):
#             continue

#         if path.is_file():

#             files.append(
#                 str(path.relative_to(root))
#             )

#     if not files:
#         return "No files found."

#     files.sort()

#     return "\n".join(files)


# def read_file(
#     file_path: str,
#     start_line: int = None,
#     end_line: int = None
# ) -> str:
#     """
#     Read the contents of a project file.

#     Optional line range:
#         start_line=10
#         end_line=30
#     """

#     path = Path(file_path)

#     if not path.exists():
#         return (
#             f"ERROR: File does not exist: "
#             f"{file_path}"
#         )

#     if not path.is_file():
#         return (
#             f"ERROR: Not a file: "
#             f"{file_path}"
#         )

#     try:

#         content = path.read_text(
#             encoding="utf-8",
#             errors="ignore"
#         )

#     except Exception as e:

#         return f"ERROR reading file: {e}"

#     lines = content.splitlines()

#     total_lines = len(lines)

#     # If no range is provided, return entire file
#     if start_line is None and end_line is None:

#         return content

#     # Default values
#     if start_line is None:
#         start_line = 1

#     if end_line is None:
#         end_line = total_lines

#     # Protect against invalid values
#     start_line = max(
#         1,
#         start_line
#     )

#     end_line = min(
#         total_lines,
#         end_line
#     )

#     selected_lines = lines[
#         start_line - 1:end_line
#     ]

#     output = []

#     for index, line in enumerate(
#         selected_lines,
#         start=start_line
#     ):

#         output.append(
#             f"{index}: {line}"
#         )

#     return "\n".join(output)


# def search_code(
#     directory: str,
#     query: str,
#     context_lines: int = 2
# ) -> str:
#     """
#     Search for terms inside project files.

#     Supports:

#         embedding

#     and also:

#         embedding|embed|model

#     Multiple terms separated by | are treated as OR.
#     """

#     root = Path(directory)

#     if not root.exists():
#         return (
#             f"ERROR: Directory does not exist: "
#             f"{directory}"
#         )

#     query = query.strip()

#     if not query:
#         return (
#             "ERROR: Search query is empty."
#         )

#     # ------------------------------------------
#     # Support OR queries
#     #
#     # embedding|embed|model
#     # ------------------------------------------

#     search_terms = [
#         term.strip()
#         for term in query.split("|")
#         if term.strip()
#     ]

#     if not search_terms:
#         return (
#             "ERROR: No valid search terms."
#         )

#     results = []

#     for path in root.rglob("*"):

#         if is_ignored(path):
#             continue

#         if not path.is_file():
#             continue

#         if path.suffix.lower() not in SEARCHABLE_EXTENSIONS:
#             continue

#         try:

#             content = path.read_text(
#                 encoding="utf-8",
#                 errors="ignore"
#             )

#         except Exception:

#             continue

#         lines = content.splitlines()

#         matched_line_numbers = []

#         for line_number, line in enumerate(
#             lines,
#             start=1
#         ):

#             line_lower = line.lower()

#             if any(
#                 term.lower() in line_lower
#                 for term in search_terms
#             ):

#                 matched_line_numbers.append(
#                     line_number
#                 )

#         if not matched_line_numbers:
#             continue

#         relative_path = path.relative_to(root)

#         # ------------------------------------------
#         # Group nearby matches
#         # ------------------------------------------

#         included_lines = set()

#         for line_number in matched_line_numbers:

#             start = max(
#                 1,
#                 line_number - context_lines
#             )

#             end = min(
#                 len(lines),
#                 line_number + context_lines
#             )

#             for number in range(
#                 start,
#                 end + 1
#             ):

#                 included_lines.add(
#                     number
#                 )

#         sorted_lines = sorted(
#             included_lines
#         )

#         results.append(
#             f"\n{relative_path}\n"
#             + "-" * len(
#                 str(relative_path)
#             )
#         )

#         previous_line = None

#         for line_number in sorted_lines:

#             # Add separator between distant matches
#             if (
#                 previous_line is not None
#                 and line_number > previous_line + 1
#             ):

#                 results.append(
#                     "..."
#                 )

#             results.append(
#                 f"{line_number}: "
#                 f"{lines[line_number - 1]}"
#             )

#             previous_line = line_number

#     if not results:

#         return (
#             "NO_MATCHES_FOUND\n\n"
#             f"The search query '{query}' "
#             "was not found in the project."
#         )

#     return "\n".join(results)