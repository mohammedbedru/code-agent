# Code Agent

A fully functional VS Code coding agent powered by your local Ollama model.

## Architecture

```
VS Code Extension (TypeScript)
        |  HTTP + SSE
        v
Backend Server (FastAPI, port 8765)
        |
        v
Ollama (local LLM)
        |
        v
Agent Tools → Your Workspace
```

## Setup

### 1. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the backend

```bash
python run_server.py
```

Or on Windows: double-click `start_server.bat`

The server runs at `http://127.0.0.1:8765`

### 3. Install the VS Code extension

```bash
cd vscode-extension
npm install
npm run compile
```

Then in VS Code:
- Press `F5` to launch Extension Development Host, or
- Package with `vsce package` and install the `.vsix`

### 4. Configure (optional)

In VS Code settings (`codeAgent.*`):

| Setting | Default | Description |
|---|---|---|
| `codeAgent.model` | `gemma4:12b` | Ollama model to use |
| `codeAgent.backendUrl` | `http://127.0.0.1:8765` | Backend URL |
| `codeAgent.confirmFileEdits` | `false` | Confirm before editing files |
| `codeAgent.confirmFileDeletion` | `true` | Confirm before deleting files |
| `codeAgent.confirmDangerousCommands` | `true` | Confirm dangerous commands |

## Usage

1. Open a workspace folder in VS Code
2. Click the Code Agent icon in the activity bar
3. Type your request and press `Ctrl+Enter` or click Send

### Example requests

- "List all files and explain the project structure"
- "Find where authentication is implemented"
- "Add error handling to the main function in app.py"
- "Run the tests and fix any failures"
- "Refactor the database module to use async/await"
- "Create a new REST endpoint for user registration"

## Tools

| Tool | Description |
|---|---|
| `list_files` | List all workspace files |
| `read_file` | Read file contents (with optional line range) |
| `search_code` | Search for text across files (supports `term1\|term2` OR) |
| `create_file` | Create a new file |
| `edit_file` | Replace exact text in a file |
| `delete_file` | Delete a file |
| `run_command` | Execute shell commands in workspace |
| `get_file_info` | Get file metadata |

## Backend Structure

```
backend/
    server.py          FastAPI server with SSE streaming
    agent.py           Agent loop + tool execution
    ollama_client.py   Ollama HTTP client
    prompts.py         System prompt
    tools/
        filesystem.py  list, read, create, edit, delete files
        search.py      Code search with context
        terminal.py    Command execution with safety checks
```
