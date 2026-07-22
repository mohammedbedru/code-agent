import json
from typing import Iterator
from . import ollama_client
from .prompts import SYSTEM_PROMPT
from .tools import filesystem, search, terminal

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the workspace",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use start_line/end_line for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file"},
                    "start_line": {"type": "integer", "description": "First line to read (1-based)"},
                    "end_line": {"type": "integer", "description": "Last line to read (1-based)"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for text in workspace files. Use | for OR searches: 'auth|login'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term(s), use | for OR"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with given content",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path for the new file"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in a file. old_text must match exactly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file"},
                    "old_text": {"type": "string", "description": "Exact text to replace"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["file_path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the workspace directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get metadata about a file (size, line count, extension)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file"},
                },
                "required": ["file_path"],
            },
        },
    },
]


def _execute_tool(workspace: str, name: str, args: dict) -> str:
    try:
        if name == "list_files":
            return filesystem.list_files(workspace)
        elif name == "read_file":
            return filesystem.read_file(workspace, args["file_path"], args.get("start_line"), args.get("end_line"))
        elif name == "search_code":
            return search.search_code(workspace, args["query"])
        elif name == "create_file":
            return filesystem.create_file(workspace, args["file_path"], args["content"])
        elif name == "edit_file":
            return filesystem.edit_file(workspace, args["file_path"], args["old_text"], args["new_text"])
        elif name == "delete_file":
            return filesystem.delete_file(workspace, args["file_path"])
        elif name == "run_command":
            result = terminal.run_command(workspace, args["command"], args.get("timeout", 60))
            parts = []
            if result["stdout"]:
                parts.append(f"STDOUT:\n{result['stdout']}")
            if result["stderr"]:
                parts.append(f"STDERR:\n{result['stderr']}")
            parts.append(f"EXIT CODE: {result['exit_code']}")
            return "\n".join(parts)
        elif name == "get_file_info":
            return filesystem.get_file_info(workspace, args["file_path"])
        else:
            return f"ERROR: Unknown tool: {name}"
    except KeyError as e:
        return f"ERROR: Missing required argument: {e}"
    except Exception as e:
        return f"ERROR: Tool execution failed: {e}"


def run_agent(workspace: str, user_message: str, history: list, model: str, settings: dict) -> Iterator[dict]:
    """
    Generator that yields SSE-style events:
      {"type": "tool_call", "tool": name, "args": {...}}
      {"type": "tool_result", "tool": name, "result": str}
      {"type": "token", "content": str}
      {"type": "done", "content": str}
      {"type": "error", "message": str}
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    max_iterations = 20

    for _ in range(max_iterations):
        try:
            response = ollama_client.chat(model=model, messages=messages, tools=TOOL_DEFINITIONS)
        except Exception as e:
            yield {"type": "error", "message": f"Ollama error: {e}"}
            return

        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls", [])

        if not tool_calls:
            content = msg.get("content", "")
            messages.append({"role": "assistant", "content": content})
            yield {"type": "done", "content": content}
            return

        messages.append(msg)

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            yield {"type": "tool_call", "tool": name, "args": args}

            result = _execute_tool(workspace, name, args)

            yield {"type": "tool_result", "tool": name, "result": result}

            messages.append({
                "role": "tool",
                "content": result,
            })

    yield {"type": "error", "message": "Agent reached maximum iterations without completing."}
