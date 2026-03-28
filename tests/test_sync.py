import pytest
import responses
import json
import sys
from unittest.mock import MagicMock, patch
from sync import is_youtube_short, sanitize_filename, _sanitize_keywords, VideoMeta, get_recent_history, get_video_details, summarize_and_tag, main, YOUTUBE_FETCH_DELAY_SECONDS

def test_sanitize_filename():
    assert sanitize_filename("Normal Title") == "Normal Title"
    assert sanitize_filename("Title with: colon") == "Title with colon"
    assert sanitize_filename('Quotes "and" \\ slashes / ?') == "Quotes and  slashes"
    assert sanitize_filename("A_B-C.D") == "A_B-C.D"
    assert sanitize_filename("  Leading and Trailing   ") == "  Leading and Trailing"
    assert sanitize_filename("???!!!") == "Untitled"

def test_sanitize_keywords():
    raw_keywords = [
        "neural network",
        "elon_musk",
        "machine-learning",
        "  spaces   ",
        "UPPERCASE",
        "duplicate",
        "Duplicate",
        "DUPLICATE",
        "123 numbers",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k" # 11 items
    ]
    
    cleaned = _sanitize_keywords(raw_keywords)
    
    # Check camel casing
    assert "NeuralNetwork" in cleaned
    assert "ElonMusk" in cleaned
    assert "MachineLearning" in cleaned
    assert "Spaces" in cleaned
    assert "UPPERCASE" in cleaned
    
    # Check deduplication (case-insensitive deduplication, keeps first occurrence's casing)
    # The first 'duplicate' becomes 'Duplicate'
    assert cleaned.count("Duplicate") == 1
    
    # Check max length (capped at 10)
    assert len(cleaned) == 10

def test_video_meta_model():
    meta = VideoMeta(video_id="123", title="Test", uploader="Channel", description="Desc")
    assert meta.video_id == "123"
    assert meta.title == "Test"
    assert meta.uploader == "Channel"
    assert meta.description == "Desc"
    
    # description is optional
    meta_no_desc = VideoMeta(video_id="123", title="Test", uploader="Channel")
    assert meta_no_desc.description is None

@responses.activate
def test_is_youtube_short_true():
    # Setup mock for a successful 200 response
    responses.add(
        responses.HEAD,
        "https://www.youtube.com/shorts/valid_short_id",
        status=200
    )
    assert is_youtube_short("valid_short_id") is True

@responses.activate
def test_is_youtube_short_false():
    # Setup mock for a 303 redirect
    responses.add(
        responses.HEAD,
        "https://www.youtube.com/shorts/regular_video_id",
        status=303
    )
    assert is_youtube_short("regular_video_id") is False

@responses.activate
def test_is_youtube_short_exception_fallback():
    # Setup mock to simulate a network error
    responses.add(
        responses.HEAD,
        "https://www.youtube.com/shorts/error_id",
        body=Exception("Connection refused")
    )
    # The function catches exceptions and returns False (errs on side of processing)
    assert is_youtube_short("error_id") is False

@patch('sync.subprocess.run')
@patch('sync.get_transcript')
def test_sync_e2e_single_file_mocked(mock_get_transcript, mock_subprocess_run):
    # Mock subprocess for get_recent_history
    history_result = MagicMock()
    history_result.stdout = "vid123|Test Video|Test Channel\n"
    
    # Mock subprocess for get_video_details
    details_result = MagicMock()
    details_result.stdout = json.dumps({
        "description": "A great test video",
        "uploader": "Test Channel"
    })
    
    # Configure subprocess mock to return the right thing based on args
    def side_effect(*args, **kwargs):
        cmd = args[0]
        if "https://www.youtube.com/feed/history" in cmd:
            return history_result
        if "--dump-json" in cmd:
            return details_result
        raise Exception(f"Unexpected command: {cmd}")
        
    mock_subprocess_run.side_effect = side_effect
    
    # Mock transcript
    mock_get_transcript.return_value = "This is a transcript."
    
    # Mock Gemini Client
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Provide exactly what ProcessedTranscript expects
    mock_response.text = json.dumps({
        "summary": "AI Summary",
        "tags": ["Technology", "Technology/ArtificialIntelligence"],
        "links": ["https://example.com"],
        "keywords": ["AI", "Test"]
    })
    mock_client.models.generate_content.return_value = mock_response

    # 1. Fetch History
    videos = get_recent_history(1)
    assert len(videos) == 1
    assert videos[0].video_id == "vid123"

    # 2. Get Details
    details = get_video_details("vid123")
    assert details["description"] == "A great test video"
    assert details["uploader"] == "Test Channel"
    
    # 3. Summarize and Tag
    processed = summarize_and_tag("Test Video", "This is a transcript.", "A great test video", mock_client)
    assert processed.summary == "AI Summary"
    assert processed.tags == ["Technology", "Technology/ArtificialIntelligence"]
    assert processed.links == ["https://example.com"]
    assert processed.keywords == ["AI", "Test"]

@patch('sys.argv', ['sync.py', '--sync'])
@patch('sync.get_recent_history')
@patch('sync.genai.Client')
@patch('sync.check_write_permissions')
@patch('os.environ.get')
def test_main_cli_sync(mock_env_get, mock_check_perms, mock_client, mock_get_history):
    # Mock GEMINI_API_KEY
    mock_env_get.return_value = "dummy_key"
    mock_get_history.return_value = [] # Return empty list to stop early
    
    # Execute main which now expects --sync
    main()
    
    # Verify get_recent_history was called with fetch_limit = None
    # because --sync parses the full history list
    mock_get_history.assert_called_once_with(None)

@patch('sys.argv', ['sync.py', '--init'])
def test_main_cli_init_fails():
    with pytest.raises(SystemExit):
        main() # Should exit because --init is no longer an argument

@patch('sys.argv', ['sync.py', '--incremental'])
def test_main_cli_incremental_fails():
    with pytest.raises(SystemExit):
        main() # Should exit because --incremental is no longer an argument
