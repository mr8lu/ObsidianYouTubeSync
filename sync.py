import os
import sys
import json
import subprocess
import html
import re
import time
import argparse
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from google import genai
from google.genai import types
from tenacity import retry, wait_random, wait_random_exponential, stop_after_attempt, stop_after_delay
from taxonomy import normalize_tags, TAXONOMY_HINT

# Configuration
OBSIDIAN_VAULT_PATH = os.path.expanduser("~/Documents/Obsidian Vault")
YOUTUBE_FOLDER = os.path.join(OBSIDIAN_VAULT_PATH, "YouTube")
FAILED_CACHE_FILE = os.path.join(YOUTUBE_FOLDER, ".failed_videos.txt")
BROWSER_FOR_COOKIES = "chrome"  # Change to 'safari', 'firefox', etc. if needed

# Proxy Config
WEBSHARE_PROXY_USER = os.environ.get("WEBSHARE_PROXY_USER")
WEBSHARE_PROXY_PASS = os.environ.get("WEBSHARE_PROXY_PASS")
YTDLP_PROXY_URL = f"http://{WEBSHARE_PROXY_USER}:{WEBSHARE_PROXY_PASS}@p.webshare.io:80/"

# Rate Limit Configs
YOUTUBE_FETCH_DELAY_SECONDS = 0.22    # Pause between history fetches (set >0 to avoid IP blocks)
GEMINI_API_DELAY_SECONDS = 0.12    # Stay safely under RPM limit for Gemini Flash
THREAD_POOL_SIZE = 2               # Parallel workers for video processing and re-tagging

def is_youtube_short(video_id: str) -> bool:
    """
    Returns True if the given video_id is a YouTube Short.
    Uses a lightweight HEAD request against the /shorts/ URL:
    - 200  → valid Short (don't process)
    - 303/3xx → redirects to /watch, meaning it's a regular video (process it)
    """
    try:
        url = f"https://www.youtube.com/shorts/{video_id}"
        response = requests.head(url, allow_redirects=False, timeout=5)
        return response.status_code == 200
    except Exception as e:
        # If the check fails, err on the side of processing the video
        print(f"  [shorts-check] Could not determine if {video_id} is a Short ({e}). Assuming regular video.")
        return False


class VideoMeta(BaseModel):
    video_id: str
    title: str
    uploader: str
    description: Optional[str] = None

class ProcessedTranscript(BaseModel):
    summary: str = Field(description="A brief summary of the video based on transcript and description. Write the summary in English or Traditional Chinese depending on the primary language of the video.")
    tags: List[str] = Field(description=(
        "Hierarchical knowledge classification tags IN ENGLISH using CamelCase and forward-slash hierarchy. "
        "Choose from this taxonomy (include parent AND child, e.g. 'Technology' AND 'Technology/ArtificialIntelligence'): "
        f"{TAXONOMY_HINT}. "
        "You MAY also generate dynamic entity tags starting with Person/, Channel/, Company/, Organization/, Product/, Location/, or Event/ (e.g. Person/ElonMusk, Company/Apple). "
        "Rules: CamelCase only (e.g. MachineLearning not machine_learning). "
        "Use '/' for hierarchy (e.g. Technology/ArtificialIntelligence/MachineLearning). "
        "No spaces, no '#'. Return 4-8 tags ordered broad-to-specific. "
        "If content doesn't fit any domain, use Other/Uncategorized."
    ))
    links: List[str] = Field(description="List of relevant URLs/links provided along with the video (e.g. from the description).")
    keywords: List[str] = Field(description=(
        "Up to 10 concise, content-specific CamelCase keywords for full-text search and collaborative filtering. "
        "Include: key concepts, technical terms, named entities (people, brands, places), jargon, notable ideas. "
        "Examples: ElonMusk, NeuralNetwork, MacBook, Fermentation, ClimateTipping, Stoicism. "
        "No taxonomy hierarchy — flat CamelCase only. No spaces, no '#', no '/'. Translate non-English terms to English."
    ))

def get_recent_history(max_fetch: Optional[int]) -> List[VideoMeta]:
    """Fetch recent YouTube history using yt-dlp and browser cookies."""
    if max_fetch:
        print(f"Fetching up to {max_fetch} recent history items from YouTube (using {BROWSER_FOR_COOKIES} cookies)...")
    else:
        print(f"Fetching FULL watch history from YouTube. This may take a while (using {BROWSER_FOR_COOKIES} cookies)...")
        
    cmd = [
        "yt-dlp",
        f"--cookies-from-browser", BROWSER_FOR_COOKIES,
        "--flat-playlist",
        "--print", "%(id)s|%(title)s|%(uploader)s",
        "https://www.youtube.com/feed/history"
    ]
    
    if WEBSHARE_PROXY_USER and WEBSHARE_PROXY_PASS:
        # Insert proxy config after yt-dlp
        cmd.insert(1, "--proxy")
        cmd.insert(2, YTDLP_PROXY_URL)
    
    if max_fetch and max_fetch > 0:
        cmd.extend(["--playlist-end", str(max_fetch)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e.stderr}")
        print("Please ensure you are logged into YouTube on your browser and try again.")
        sys.exit(1)
        
    videos = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|', 2)
        if len(parts) == 3:
            videos.append(VideoMeta(video_id=parts[0], title=parts[1], uploader=parts[2]))
            
    return videos

@retry(wait=wait_random(min=10, max=20), stop=stop_after_attempt(3), reraise=True)
def get_video_details(video_id: str) -> Dict[str, str]:
    """Fetch video description and channel name using yt-dlp."""
    cmd = [
        "yt-dlp",
        f"--cookies-from-browser", BROWSER_FOR_COOKIES,
        "--dump-json",
        "--no-download",
        "--skip-download",
        "--ignore-no-formats-error",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    if WEBSHARE_PROXY_USER and WEBSHARE_PROXY_PASS:
        cmd.insert(1, "--proxy")
        cmd.insert(2, YTDLP_PROXY_URL)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        description = data.get("description", "") or ""
        uploader = data.get("channel") or data.get("uploader") or ""
        
        # Validations enforcing strict requirements
        if not description.strip() or not uploader.strip() or uploader == "Unknown Channel":
            raise Exception("Missing mandatory description or channel uploader")
            
        return {
            "description": description,
            "uploader": uploader
        }
    except Exception as e:
        print(f"    (Retrying get_video_details... Error: {e})")
        raise e

@retry(wait=wait_random(min=10, max=20), stop=stop_after_attempt(3), reraise=True)
def get_transcript(video_id: str) -> Optional[str]:
    """Extract transcript for a given video ID."""
    print(f"  Fetching transcript for video {video_id}...")
    try:
        proxy_config = WebshareProxyConfig(
            proxy_username=WEBSHARE_PROXY_USER,
            proxy_password=WEBSHARE_PROXY_PASS
        )
        api = YouTubeTranscriptApi(proxy_config=proxy_config)
        transcript_list = api.list(video_id)
        
        # Try to find english, traditional chinese, or simplified chinese transcripts,
        # or just fallback to whatever might be available.
        try:
            transcript = transcript_list.find_transcript(['en', 'zh-TW', 'zh-Hant', 'zh-CN', 'zh-Hans', 'zh'])
        except Exception:
            # Fallback to the first available transcript if native preferred languages aren't found
            transcript = next(iter(transcript_list))
            
            # If it's translatable, translate it to English or Chinese
            if hasattr(transcript, 'translation_languages'):
                for lang in ['en', 'zh-TW', 'zh-Hant', 'zh-CN', 'zh-Hans', 'zh']:
                    if any(t.language_code == lang for t in transcript.translation_languages):
                        transcript = transcript.translate(lang)
                        break
            
        fetched = transcript.fetch()
        
        # Combine text
        full_text = " ".join([item.text for item in fetched])
        
        # Clean up HTML entities
        return html.unescape(full_text)
    except Exception as e:
        print(f"    (Retrying get_transcript... Error: {e})")
        raise e

@retry(wait=wait_random_exponential(multiplier=1.5, max=20), stop=stop_after_attempt(3), reraise=True)
def summarize_and_tag(title: str, transcript: str, description: str, client: genai.Client) -> ProcessedTranscript:
    """Use Gemini to summarize and generate tags."""
    print("  Generating summary, tags, and links with Gemini...")
    transcript_text = transcript[:100000] if transcript else "No transcript available."
    prompt = (
        f"Analyze the following YouTube video and return a structured JSON response.\n\n"
        f"Title:\n{title}\n\n"
        f"Description:\n{description[:3000]}\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"For the tags field, pick 4-8 hierarchical CamelCase tags from this taxonomy:\n{TAXONOMY_HINT}\n"
        f"You may also generate dynamic entity tags if relevant, using prefixes Person/, Channel/, Company/, Organization/, Product/, Location/, or Event/ (e.g., Person/ElonMusk).\n"
        f"Include both parent and child nodes (e.g. 'Technology' AND 'Technology/ArtificialIntelligence'). "
        f"Use Other/Uncategorized only if no domain fits.\n"
        f"For the keywords field, extract up to 10 specific CamelCase content keywords: key concepts, technical terms, named entities, jargon, notable ideas. "
        f"These are for search and collaborative filtering — be informative and specific."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProcessedTranscript,
            ),
        )
        result = ProcessedTranscript.model_validate_json(response.text)
        # Normalize and validate tags against taxonomy immediately after generation
        result.tags = normalize_tags(result.tags)
        # Sanitize keywords: strip illegal chars, enforce CamelCase, deduplicate, cap at 10
        result.keywords = _sanitize_keywords(result.keywords)
        return result
    except Exception as e:
        print(f"    (Retrying Gemini Summarize... Error: {e})")
        raise e

def sanitize_filename(name: str) -> str:
    """Make string safe for Obsidian filename."""
    keepcharacters = (' ', '.', '_', '-')
    sanitized = "".join(c for c in name if c.isalnum() or c in keepcharacters).rstrip()
    return sanitized if sanitized else "Untitled"

def _sanitize_keywords(raw: List[str]) -> List[str]:
    """
    Clean up free-form keywords: split on word boundaries, CamelCase each word,
    join into a single token, deduplicate (case-insensitive), cap at 10.
    e.g. "neural network" -> "NeuralNetwork", "elon_musk" -> "ElonMusk"
    """
    seen: set = set()
    result = []
    for kw in raw:
        # Split on any non-alphanumeric boundary
        words = re.split(r"[\s_\-]+", kw.strip())
        # CamelCase each non-empty word segment (preserve Unicode chars, strip punctuation)
        words_clean = [re.sub(r'[^\w]', '', w, flags=re.UNICODE) for w in words if w]
        camel = "".join((w[0].upper() + w[1:]) for w in words_clean if w)
        if not camel or camel.lower() in seen:
            continue
        seen.add(camel.lower())
        result.append(camel)
        if len(result) >= 10:
            break
    return result

def save_to_obsidian(video: VideoMeta, processed: ProcessedTranscript, transcript: str):
    """Save the processed data as a Markdown file in Obsidian."""
    os.makedirs(YOUTUBE_FOLDER, exist_ok=True)
    
    filename = f"{sanitize_filename(video.title)}.md"
    filepath = os.path.join(YOUTUBE_FOLDER, filename)
    
    if os.path.exists(filepath):
        print(f"  File {filename} already exists. Skipping.")
        return False
        
    url = f"https://www.youtube.com/watch?v={video.video_id}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Normalize tags through taxonomy (already done in summarize_and_tag, but belt-and-suspenders)
    clean_tags = normalize_tags(processed.tags)
    clean_keywords = _sanitize_keywords(processed.keywords)
    # Merge all into the Obsidian `tags:` property so they're searchable as native tags
    all_tags = list(dict.fromkeys(clean_tags + clean_keywords))  # dedup, preserve order
    tags_str = "\n".join([f"  - {t}" for t in all_tags])
    links_str = "\n".join([f"- {l}" for l in processed.links]) if processed.links else "- No links found in description/video."
    
    # Properly escape quotes in the summary for YAML
    safe_summary = processed.summary.replace('"', '\\"').replace('\n', ' ')
    
    content = f"""---
url: {url}
channel: "{video.uploader}"
date_synced: {date_str}
summary: "{safe_summary}"
tags:
{tags_str}
---

# {video.title}

## Extracted Links
{links_str}

## Source Link
[{video.title}]({url})

## Description
{video.description if video.description else "No description available."}

## Raw Transcript
```text
{transcript}
```
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"  -> Saved to {filepath}")
    return True

def check_write_permissions(path: str):
    """Ensure the program has write permissions to the specified directory."""
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception as e:
        print(f"Error: Cannot write to '{path}'.")
        print("Please ensure this program has the correct permissions (e.g. macOS Documents folder access) to write here.")
        print(f"Details: {e}")
        sys.exit(1)

def load_failed_cache() -> set:
    """Load the set of continually failing video IDs from cache."""
    if not os.path.exists(FAILED_CACHE_FILE):
        return set()
    with open(FAILED_CACHE_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def add_to_failed_cache(video_id: str):
    """Append a video ID to the failure cache."""
    with open(FAILED_CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

def check_cookie_status():
    """Diagnose yt-dlp cookie extraction issues."""
    print(f"\nTesting cookie extraction from '{BROWSER_FOR_COOKIES}'...")
    print("Running diagnostic command: yt-dlp --cookies-from-browser ...\n")
    
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", BROWSER_FOR_COOKIES,
        "--dump-json",
        "https://www.youtube.com/feed/history",
        "--playlist-end", "1"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check stderr for warnings
        if "WARNING" in result.stderr or "Could not extract" in result.stderr or result.returncode != 0:
            print("❌ COOKIE EXTRACTION FAILED\n")
            print("yt-dlp encountered the following error:")
            print(f"{result.stderr.strip()}\n")
            
            print("--- COMMON MACOS FIXES ---")
            print("1. Full Disk Access (Most Common):")
            print("   Go to System Settings > Privacy & Security > Full Disk Access.")
            print("   Ensure your Terminal (or VS Code, Cursor, iTerm) is toggled ON.")
            print(f"\n2. {BROWSER_FOR_COOKIES.capitalize()} is Running:")
            print(f"   Browsers lock their cookie database while open. Try completely quitting")
            print(f"   {BROWSER_FOR_COOKIES.capitalize()} (Cmd+Q) and running this command again.")
            print("\n3. Wrong Profile:")
            print(f"   If your YouTube account is not on the default profile, edit sync.py:")
            print(f"   BROWSER_FOR_COOKIES = \"{BROWSER_FOR_COOKIES}:Profile 2\"")
            return
            
        # Check stdout for valid JSON response (indicating success)
        if result.stdout.strip():
            print("✅ COOKIES EXTRACTED SUCCESSFULLY\n")
            print("Authentication with YouTube worked perfectly. We found recent history.")
            return
            
        # If no warnings and no output, likely history is just empty
        print("⚠️ COOKIES EXTRACTED, BUT HISTORY IS EMPTY\n")
        print(f"yt-dlp successfully accessed {BROWSER_FOR_COOKIES}, but the YouTube history feed")
        print("returned an empty playlist. Please check:")
        print(" - Is your YouTube watch history paused in your Google Account settings?")
        print(f" - Are you logged into the correct Google account on {BROWSER_FOR_COOKIES}?")
        
    except FileNotFoundError:
        print("❌ ERROR: 'yt-dlp' is not installed or not found in your PATH.")
        print("Are you running this inside the virtual environment? (e.g. ./run.sh)")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

def retag_existing_notes(client: genai.Client):
    """
    --retag mode: Re-examine all existing Obsidian YouTube notes, re-run Gemini tagging
    against the stored title + description + transcript, and overwrite only the tags
    block in the YAML frontmatter. No YouTube network calls are made.
    Runs in parallel using THREAD_POOL_SIZE workers.
    """
    md_files = sorted(
        os.path.join(YOUTUBE_FOLDER, f)
        for f in os.listdir(YOUTUBE_FOLDER)
        if f.endswith(".md")
    )

    if not md_files:
        print("No existing notes found in", YOUTUBE_FOLDER)
        return

    total = len(md_files)
    print(f"Found {total} existing note(s) to re-tag (pool size: {THREAD_POOL_SIZE}).")
    counter = threading.Lock()
    completed = [0]  # mutable int inside list for thread-safe increment

    def retag_one(filepath: str):
        filename = os.path.basename(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not fm_match:
            with counter:
                completed[0] += 1
                print(f"[{completed[0]}/{total}] {filename}: Skipping — no YAML frontmatter.")
            return

        frontmatter_raw = fm_match.group(1)

        title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename.replace(".md", "")

        desc_match = re.search(r"## Description\n(.*?)(?=\n## |$)", content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        transcript_match = re.search(r"## Raw Transcript\n```text\n(.*?)\n```", content, re.DOTALL)
        transcript = transcript_match.group(1).strip() if transcript_match else ""

        old_tags_match = re.search(r"^tags:\n((?:  - .+\n?)*)", frontmatter_raw, re.MULTILINE)
        old_tags = []
        if old_tags_match:
            old_tags = [l.strip().lstrip("- ") for l in old_tags_match.group(1).strip().splitlines()]

        time.sleep(GEMINI_API_DELAY_SECONDS)
        try:
            processed = summarize_and_tag(title, transcript, description, client)
        except Exception as e:
            with counter:
                completed[0] += 1
                print(f"[{completed[0]}/{total}] {filename}: Gemini failed: {e}. Skipping.")
            return

        new_tags = processed.tags
        clean_keywords = _sanitize_keywords(processed.keywords)
        all_new_tags = list(dict.fromkeys(new_tags + clean_keywords))

        added = set(all_new_tags) - set(old_tags)
        removed = set(old_tags) - set(all_new_tags)

        new_tags_yaml = "\n".join([f"  - {t}" for t in all_new_tags])
        new_frontmatter = re.sub(
            r"(^tags:\n)((?:  - .+\n?)*)",
            f"tags:\n{new_tags_yaml}\n",
            frontmatter_raw,
            flags=re.MULTILINE
        )
        new_content = content.replace(frontmatter_raw, new_frontmatter, 1)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        with counter:
            completed[0] += 1
            idx = completed[0]
            if added or removed:
                removed_str = "".join(f"\n    - {t}" for t in sorted(removed))
                added_str = "".join(f"\n    + {t}" for t in sorted(added))
                print(f"[{idx}/{total}] {filename}: tags changed{removed_str}{added_str}")
            else:
                print(f"[{idx}/{total}] {filename}: tags unchanged")

    with ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
        futures = {executor.submit(retag_one, fp): fp for fp in md_files}
        try:
            for future in as_completed(futures):
                future.result()  # Propagate any unhandled exception
        except KeyboardInterrupt:
            print("\nInterrupted. Cancelling remaining tasks...")
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    print("\nRe-tagging complete.")


def main():
    parser = argparse.ArgumentParser(description="Sync YouTube watch history to Obsidian Vault.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sync", action="store_true", help="Sync full YouTube watch history (skips already existing files). Throttling is always enabled.")
    group.add_argument("--test", action="store_true", help="Test the script by fetching exactly 1 recent video.")
    group.add_argument("--retag", action="store_true", help="Re-examine and overwrite tags in all existing Obsidian notes using the current taxonomy. No YouTube data is re-fetched.")
    group.add_argument("--check-cookies", action="store_true", help="Diagnose browser cookie extraction and YouTube authentication")
    parser.add_argument("--no-transcript", action="store_true", help="Skip transcript retrieval step.")
    args = parser.parse_args()

    if args.check_cookies:
        check_cookie_status()
        return
    
    # --sync mode pulls all history (None). Test pulls 1.
    if args.test:
        fetch_limit = 1
    elif args.sync:
        fetch_limit = None
    elif args.retag:
        fetch_limit = 0  # No YouTube fetch needed
    else:
        fetch_limit = None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please run: export GEMINI_API_KEY='your_key_here'")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    # Verify we can write to our destination folders before starting long-running fetching
    check_write_permissions(OBSIDIAN_VAULT_PATH)
    check_write_permissions(os.path.join(OBSIDIAN_VAULT_PATH, "YouTube"))

    # --retag: re-examine and overwrite tags in all existing notes, then exit
    if args.retag:
        retag_existing_notes(client)
        return

    videos = get_recent_history(fetch_limit)
    print(f"Found {len(videos)} videos in recent history.")
    
    videos_to_process = []
    shorts_skipped = 0
    for video in videos:
        filename = f"{sanitize_filename(video.title)}.md"
        filepath = os.path.join(YOUTUBE_FOLDER, filename)
        
        # NOTE: Incremental mode behaves like init mode in that it uses continue
        # but the actual fetch limit restricts how far down the history it looks.
        if os.path.exists(filepath):
            continue

        if is_youtube_short(video.video_id):
            print(f"  [skip] {video.title} ({video.video_id}) is a YouTube Short. Skipping.")
            shorts_skipped += 1
            continue

        videos_to_process.append(video)

    # Load failed cache and filter videos to process
    failed_cache = load_failed_cache()
    if failed_cache:
        original_count = len(videos_to_process)
        videos_to_process = [v for v in videos_to_process if v.video_id not in failed_cache]
        skipped_failed = original_count - len(videos_to_process)
        if skipped_failed > 0:
            print(f"Skipped {skipped_failed} previously failed video(s) found in cache.")

    if shorts_skipped:
        print(f"Skipped {shorts_skipped} YouTube Short(s).")

    # Process from oldest to latest
    videos_to_process.reverse()
    print(f"Queueing {len(videos_to_process)} new videos to process (oldest to newest)...")
    
    processed_count = 0
    processed_lock = threading.Lock()
    delayed_queue: List = []
    delayed_lock = threading.Lock()

    def process_video(video, try_number=1, is_delayed=False):
        # Throttle processing to prevent IP blocking across threads
        if not is_delayed:
            time.sleep(YOUTUBE_FETCH_DELAY_SECONDS)
        
        nonlocal processed_count
        start_time = time.time()

        with processed_lock:
            processed_count += 1
            idx_display = processed_count
        total = len(videos_to_process)
        print(f"\nProcessing [{idx_display}/{total}]: {video.title} ({video.video_id})")

        try:
            filename = f"{sanitize_filename(video.title)}.md"
            filepath = os.path.join(YOUTUBE_FOLDER, filename)

            if os.path.exists(filepath):
                return "SKIPPED"

            print(f"  [{video.video_id}] Fetching details...")
            details = get_video_details(video.video_id)
            video.description = details["description"]
            video.uploader = details["uploader"]

            if time.time() - start_time > 30:
                raise Exception("Exceeded 30s wall-time limit during details API fetch.")

            transcript = None
            if args.no_transcript:
                print(f"  [{video.video_id}] Skipping transcript (--no-transcript).")
            elif time.time() - start_time < 25:
                print(f"  [{video.video_id}] Fetching transcript...")
                try:
                    transcript = get_transcript(video.video_id)
                except Exception as e:
                    print(f"  [{video.video_id}] Transcript unavailable: {e}.")
            else:
                print(f"  [{video.video_id}] Skipping transcript (time: {int(time.time() - start_time)}s).")

            if time.time() - start_time > 30:
                raise Exception("Exceeded 30s wall-time limit before Gemini generation.")

            time.sleep(GEMINI_API_DELAY_SECONDS)
            processed = summarize_and_tag(video.title, transcript or "", video.description, client)

            if not transcript:
                transcript = "No transcript could be pulled (e.g., subtitles are disabled or timed out)."

            save_to_obsidian(video, processed, transcript)
            return "SUCCESS"

        except Exception as e:
            time_elapsed = int(time.time() - start_time)
            print(f"  [{video.video_id}] Error ({time_elapsed}s): {e}")
            return "DELAY"

    stop_event = threading.Event()

    with ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
        futures = {executor.submit(process_video, v): v for v in videos_to_process}
        try:
            for future in as_completed(futures):
                status = future.result()
                if status == "DELAY":
                    video = futures[future]
                    with delayed_lock:
                        delayed_queue.append(video)
        except KeyboardInterrupt:
            print("\nInterrupted. Cancelling remaining tasks...")
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Re-run for failed items sequentially (jitter reset)
    if delayed_queue:
        print(f"\nProcessing {len(delayed_queue)} deferred video(s) sequentially...")
        for idx, video in enumerate(delayed_queue):
            print(f"\n[RETRY {idx + 1}/{len(delayed_queue)}]: {video.title} ({video.video_id})")
            if idx > 0:
                time.sleep(YOUTUBE_FETCH_DELAY_SECONDS)
            status = process_video(video, try_number=2, is_delayed=True)
            if status == "DELAY":
                print(f"  -> Video continuously failing. Adding to failure cache.")
                add_to_failed_cache(video.video_id)

    print("\nSync complete!")

if __name__ == "__main__":
    main()
