"""
retag_notes.py — Apply taxonomy-consistent tags to Obsidian markdown notes.

Scans a target folder (default: Apple Notes) for all .md files, excluding:
  - /Templates and any path containing 'template' (case-insensitive)
  - Hidden directories (e.g. .obsidian, .trash, .git)

For each note found:
  1. Reads the existing frontmatter + body content
  2. Sends title + existing tags + body to Gemini for taxonomy-aware re-tagging
  3. Overwrites ONLY the `tags:` block in the frontmatter (preserves all other content)
  4. Prints a +/- diff of old vs new tags

Runs in parallel. Uses the shared taxonomy.py for global consistency across
YouTube notes and Apple Notes.

Usage:
    python3 retag_notes.py [--folder PATH] [--dry-run] [--workers N]

Examples:
    python3 retag_notes.py
    python3 retag_notes.py --folder "/Users/[user name]/Documents/Obsidian Vault/Books"
    python3 retag_notes.py --dry-run
    python3 retag_notes.py --workers 10
"""

import os
import re
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from taxonomy import normalize_tags, TAXONOMY_HINT, DYNAMIC_PREFIXES

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OBSIDIAN_VAULT_PATH = "/Users/[user name]/Documents/Obsidian Vault"
DEFAULT_TARGET_FOLDER = os.path.join(OBSIDIAN_VAULT_PATH, "Apple Notes")

GEMINI_API_DELAY_SECONDS = 0.12   # Stay under Gemini RPM limit
THREAD_POOL_SIZE = 25             # Parallel workers

# Folder names / path fragments to always skip (case-insensitive)
EXCLUDE_PATH_FRAGMENTS = ["template", ".obsidian", ".trash", ".git"]

# ---------------------------------------------------------------------------
# Pydantic schema for Gemini response (tags + keywords only — no summary)
# ---------------------------------------------------------------------------
class NoteTagResult(BaseModel):
    tags: List[str] = Field(description=(
        "Hierarchical knowledge classification tags IN ENGLISH using CamelCase and forward-slash hierarchy. "
        "Choose from this taxonomy (include parent AND child, e.g. 'Technology' AND 'Technology/ArtificialIntelligence'): "
        f"{TAXONOMY_HINT}. "
        "You MAY also generate dynamic entity tags using prefixes: "
        f"{', '.join(p.rstrip('/') + '/' for p in DYNAMIC_PREFIXES)} "
        "(e.g. Person/ElonMusk, Company/Apple, Channel/MKBHD). "
        "Chinese entity names are allowed in dynamic tags (e.g. Person/查尼). "
        "CamelCase only. No spaces, no '#'. Return 4-10 tags ordered broad-to-specific. "
        "If content doesn't fit any domain, use Other/Uncategorized."
    ))
    keywords: List[str] = Field(description=(
        "Up to 10 concise, content-specific CamelCase keywords for search and collaborative filtering. "
        "Include key concepts, technical terms, named entities, jargon. "
        "Flat CamelCase only — no '/', no spaces. Translate non-English to English where relevant."
    ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sanitize_keywords(raw: List[str]) -> List[str]:
    """Split on word boundaries, CamelCase each segment, deduplicate, cap at 10."""
    seen: set = set()
    result = []
    for kw in raw:
        words = re.split(r"[\s_\-]+", kw.strip())
        words_clean = [re.sub(r"[^\w]", "", w, flags=re.UNICODE) for w in words if w]
        camel = "".join((w[0].upper() + w[1:]) for w in words_clean if w)
        if not camel or camel.lower() in seen:
            continue
        seen.add(camel.lower())
        result.append(camel)
        if len(result) >= 10:
            break
    return result


def _is_excluded(filepath: str) -> bool:
    """Return True if the file path contains any excluded fragment."""
    lower = filepath.lower()
    return any(frag in lower for frag in EXCLUDE_PATH_FRAGMENTS)


def _collect_md_files(root: str) -> List[str]:
    """
    Recursively collect all .md files under root, excluding:
    - Paths matching EXCLUDE_PATH_FRAGMENTS
    - Files with no readable content
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs in-place (prevents os.walk descending into them)
        dirnames[:] = [
            d for d in dirnames
            if not any(frag in d.lower() for frag in EXCLUDE_PATH_FRAGMENTS)
        ]
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            fullpath = os.path.join(dirpath, fname)
            if not _is_excluded(fullpath):
                found.append(fullpath)
    return sorted(found)


def _extract_file_parts(content: str, filename: str):
    """
    Parse a markdown file into its components.
    Returns (title, frontmatter_raw, existing_tags, body_text).
    frontmatter_raw is None if no --- block is present (orphan without frontmatter).
    """
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename.replace(".md", "")

    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not fm_match:
        return title, None, [], content

    frontmatter_raw = fm_match.group(1)

    # Existing tags — handle both YAML list style and inline bracket style
    existing_tags: List[str] = []

    # Style 1: tags: [a, b, c]
    inline_match = re.search(r"^tags:\s*\[([^\]]*)\]", frontmatter_raw, re.MULTILINE)
    if inline_match:
        raw_list = inline_match.group(1)
        existing_tags = [t.strip().strip('"\'') for t in raw_list.split(",") if t.strip()]
    else:
        # Style 2: tags:\n  - a\n  - b
        block_match = re.search(r"^tags:\n((?:  - .+\n?)*)", frontmatter_raw, re.MULTILINE)
        if block_match:
            existing_tags = [
                l.strip().lstrip("- ")
                for l in block_match.group(1).strip().splitlines()
            ]

    body = content[fm_match.end():]
    return title, frontmatter_raw, existing_tags, body


def _build_prompt(title: str, existing_tags: List[str], body: str) -> str:
    """Build the Gemini prompt for re-tagging a note."""
    existing_str = ", ".join(existing_tags) if existing_tags else "none"
    body_preview = body[:4000].strip() if body else "No body content."
    return (
        f"You are a knowledge librarian. Re-tag the following note using the taxonomy.\n\n"
        f"Title: {title}\n\n"
        f"Existing tags (for reference, may use different style): {existing_str}\n\n"
        f"Note content:\n{body_preview}\n\n"
        f"For the tags field, pick 4-10 hierarchical CamelCase tags from this taxonomy:\n{TAXONOMY_HINT}\n"
        f"You may also generate dynamic entity tags using prefixes Person/, Channel/, Company/, "
        f"Organization/, Product/, Location/, Event/ (e.g. Person/ElonMusk). "
        f"Chinese entity names are allowed (e.g. Person/查尼). "
        f"Include both parent and child nodes. Use Other/Uncategorized only if no domain fits.\n"
        f"For the keywords field, extract up to 10 specific CamelCase content keywords for search. "
        f"Be informative and specific."
    )


def _overwrite_tags_in_frontmatter(content: str, frontmatter_raw: Optional[str], all_new_tags: List[str]) -> str:
    """
    Replace the tags block in frontmatter. If no frontmatter exists, prepend one.
    """
    new_tags_yaml = "\n".join([f"  - {t}" for t in all_new_tags])

    if frontmatter_raw is None:
        # Orphan file: inject a minimal frontmatter
        injected_fm = f"---\ntags:\n{new_tags_yaml}\n---\n"
        return injected_fm + content

    # Replace inline style [a,b,c] OR block style
    # Try inline first
    inline_match = re.search(r"^tags:\s*\[[^\]]*\]", frontmatter_raw, re.MULTILINE)
    if inline_match:
        new_fm = frontmatter_raw[:inline_match.start()] + f"tags:\n{new_tags_yaml}" + frontmatter_raw[inline_match.end():]
    else:
        new_fm = re.sub(
            r"(^tags:\n)((?:  - .+\n?)*)",
            f"tags:\n{new_tags_yaml}\n",
            frontmatter_raw,
            flags=re.MULTILINE
        )
        # If no tags block existed at all, append one
        if "tags:" not in new_fm:
            new_fm = new_fm.rstrip() + f"\ntags:\n{new_tags_yaml}\n"

    return content.replace(frontmatter_raw, new_fm, 1)


# ---------------------------------------------------------------------------
# Main retag logic
# ---------------------------------------------------------------------------
def retag_notes(
    target_folder: str,
    client: genai.Client,
    dry_run: bool = False,
    workers: int = THREAD_POOL_SIZE,
):
    md_files = _collect_md_files(target_folder)
    if not md_files:
        print(f"No .md files found in {target_folder}")
        return

    total = len(md_files)
    relative = os.path.relpath(target_folder, OBSIDIAN_VAULT_PATH)
    print(f"\nFound {total} note(s) in '{relative}' (excluding Templates/hidden dirs)")
    print(f"Mode: {'DRY RUN \u2014 no files will be written' if dry_run else 'LIVE \u2014 files will be updated'}")
    print(f"Workers: {workers}\n")

    counter_lock = threading.Lock()
    completed = [0]

    def retag_one(filepath: str):
        filename = os.path.relpath(filepath, target_folder)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        title, frontmatter_raw, old_tags, body = _extract_file_parts(content, os.path.basename(filepath))

        prompt = _build_prompt(title, old_tags, body)

        time.sleep(GEMINI_API_DELAY_SECONDS)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NoteTagResult,
                ),
            )
            result = NoteTagResult.model_validate_json(response.text)
        except Exception as e:
            with counter_lock:
                completed[0] += 1
                print(f"[{completed[0]}/{total}] {filename}: Gemini failed: {e}. Skipping.")
            return

        new_tax_tags = normalize_tags(result.tags)
        new_keywords = _sanitize_keywords(result.keywords)
        all_new_tags = list(dict.fromkeys(new_tax_tags + new_keywords))

        added = set(all_new_tags) - set(old_tags)
        removed = set(old_tags) - set(all_new_tags)

        if not dry_run:
            new_content = _overwrite_tags_in_frontmatter(content, frontmatter_raw, all_new_tags)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

        with counter_lock:
            completed[0] += 1
            idx = completed[0]
            no_fm_marker = " [no frontmatter \u2192 injected]" if frontmatter_raw is None else ""
            if added or removed:
                removed_str = "".join(f"\n    - {t}" for t in sorted(removed))
                added_str = "".join(f"\n    + {t}" for t in sorted(added))
                print(f"[{idx}/{total}] {filename}{no_fm_marker}: tags changed{removed_str}{added_str}")
            else:
                print(f"[{idx}/{total}] {filename}: tags unchanged")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(retag_one, fp): fp for fp in md_files}
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("\nInterrupted. Cancelling remaining tasks...")
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    action = "Would update" if dry_run else "Updated"
    print(f"\n{action} {total} note(s). Re-tagging complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Re-tag Obsidian markdown notes using the shared taxonomy for global consistency."
    )
    parser.add_argument(
        "--folder",
        default=DEFAULT_TARGET_FOLDER,
        help=f"Target folder to scan (default: {DEFAULT_TARGET_FOLDER})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what tags would change without writing any files."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=THREAD_POOL_SIZE,
        help=f"Number of parallel Gemini workers (default: {THREAD_POOL_SIZE})"
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Run: export GEMINI_API_KEY='your_key_here'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    if not os.path.isdir(args.folder):
        print(f"Error: folder not found: {args.folder}")
        sys.exit(1)

    retag_notes(
        target_folder=args.folder,
        client=client,
        dry_run=args.dry_run,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
