from mcp.server.fastmcp import FastMCP
import subprocess
import os

# Initialize FastMCP server
mcp = FastMCP("YouTubeSyncTool")

@mcp.tool()
def sync_youtube_history(mode: str) -> str:
    """
    Synchronizes YouTube history to the local Obsidian Vault.
    
    Args:
        mode: The type of sync to perform. Allowed values: 'incremental', 'init', 'retag', 'test'.
    """
    allowed_modes = ["incremental", "init", "retag", "test"]
    if mode not in allowed_modes:
        return f"Error: Invalid mode '{mode}'. Allowed modes are: {', '.join(allowed_modes)}"
        
    script_path = os.path.join(os.path.dirname(__file__), "run.sh")
    
    try:
        # Run the bash script with the argument
        result = subprocess.run(
            [script_path, f"--{mode}"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return f"Successfully ran sync with mode '--{mode}'.\n\nOutput:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Error running sync. Mode: '--{mode}'.\nExit Code: {e.returncode}\n\nStdout:\n{e.stdout}\n\nStderr:\n{e.stderr}"

@mcp.tool()
def retag_obsidian_notes(folder: str = None, dry_run: bool = False) -> str:
    """
    Retags Markdown notes in an Obsidian Vault using the AI taxonomy.
    
    Args:
        folder: The absolute path to the directory to scan. If not provided, defaults to the regular retag config (Apple Notes).
        dry_run: If True, simulates the process without modifying any files.
    """
    python_exec = os.path.join(os.path.dirname(__file__), "venv", "bin", "python3")
    script_path = os.path.join(os.path.dirname(__file__), "retag_notes.py")
    
    args = [python_exec, script_path]
    if dry_run:
        args.append("--dry-run")
    if folder:
        args.append("--folder")
        args.append(folder)
        
    try:
        result = subprocess.run(
            args, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return f"Successfully ran retag notes.\n\nOutput:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Error running retag notes.\nExit Code: {e.returncode}\n\nStdout:\n{e.stdout}\n\nStderr:\n{e.stderr}"

if __name__ == "__main__":
    mcp.run()
