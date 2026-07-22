import subprocess
import os
from pathlib import Path

DANGEROUS_PATTERNS = [
    "rm -rf /", "rmdir /s /q c:\\", "format c:",
    "dd if=", ":(){:|:&};:", "mkfs",
]


def is_dangerous(command: str) -> bool:
    cmd_lower = command.lower()
    return any(p in cmd_lower for p in DANGEROUS_PATTERNS)


def run_command(workspace: str, command: str, timeout: int = 60) -> dict:
    if is_dangerous(command):
        return {
            "stdout": "",
            "stderr": f"BLOCKED: Command flagged as dangerous: {command}",
            "exit_code": -1,
            "blocked": True,
        }

    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists():
        return {
            "stdout": "",
            "stderr": f"ERROR: Workspace does not exist: {workspace}",
            "exit_code": -1,
        }

    env = os.environ.copy()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "stdout": result.stdout[-8000:] if result.stdout else "",
            "stderr": result.stderr[-4000:] if result.stderr else "",
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"ERROR: Command timed out after {timeout}s",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"ERROR: {e}",
            "exit_code": -1,
        }
