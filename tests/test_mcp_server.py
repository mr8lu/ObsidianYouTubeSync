import pytest
from unittest.mock import MagicMock, patch
import subprocess
import os

# Create a mock for the decorator that returns the function as is
def mock_tool_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

# Mock the FastMCP class and its tool method before importing the server
with patch('mcp.server.fastmcp.FastMCP') as MockMCP:
    MockMCP.return_value.tool = mock_tool_decorator
    from mcp_server import sync_youtube_history, retag_obsidian_notes

def test_sync_youtube_history_invalid_mode():
    result = sync_youtube_history("invalid")
    assert "Error: Invalid mode 'invalid'" in result
    assert "Allowed modes are: sync, retag, test, check-cookies" in result

@patch('subprocess.run')
def test_sync_youtube_history_success(mock_run):
    mock_run.return_value = MagicMock(stdout="Success output", returncode=0)
    
    result = sync_youtube_history("test")
    
    # Verify subprocess call
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0][-1] == "--test"
    
    assert "Successfully ran sync with mode '--test'" in result
    assert "Success output" in result

@patch('subprocess.run')
def test_sync_youtube_history_failure(mock_run):
    # Mock a CalledProcessError
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, 
        cmd=["run.sh", "--test"], 
        output="Standard out", 
        stderr="Error out"
    )
    
    result = sync_youtube_history("test")
    
    assert "Error running sync" in result
    assert "Exit Code: 1" in result
    assert "Stdout:\nStandard out" in result
    assert "Stderr:\nError out" in result

@patch('subprocess.run')
def test_retag_obsidian_notes_defaults(mock_run):
    mock_run.return_value = MagicMock(stdout="Retag success", returncode=0)
    
    result = retag_obsidian_notes()
    
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "retag_notes.py" in args[0][2]
    assert len(args[0]) == 3 # uv, run, and script_path
    
    assert "Successfully ran retag notes" in result

@patch('subprocess.run')
def test_retag_obsidian_notes_with_args(mock_run):
    mock_run.return_value = MagicMock(stdout="Retag success with args", returncode=0)
    
    result = retag_obsidian_notes(folder="/some/path", dry_run=True)
    
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "--dry-run" in args[0]
    assert "--folder" in args[0]
    assert "/some/path" in args[0]
    
    assert "Successfully ran retag notes" in result
