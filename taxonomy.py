"""
taxonomy.py — Canonical tag registry for YouTubeSyncTool.

Provides:
  TAXONOMY_TREE   — nested dict of the full hierarchy
  TAXONOMY_FLAT   — flat set of every valid tag in "Domain/Sub/Leaf" form
  normalize_tags  — validates, CamelCases, deduplicates, and expands hierarchy
  TAXONOMY_HINT   — compact string injected into Gemini prompts
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Dynamic Prefixes
# These top-level domains allow the LLM to generate arbitrary CamelCase
# leaves for specific entities (people, channels, companies, etc.)
# ---------------------------------------------------------------------------
DYNAMIC_PREFIXES = (
    "Person/",
    "Channel/",
    "Company/",
    "Organization/",
    "Product/",
    "Location/",
    "Event/"
)

# ---------------------------------------------------------------------------
# Canonical Taxonomy
# Keys are domain roots; values are recursive dicts (leaves have empty dicts)
# ALL names must be CamelCase with no spaces.
# ---------------------------------------------------------------------------
TAXONOMY_TREE: dict = {
    "Technology": {
        "ArtificialIntelligence": {
            "MachineLearning": {},
            "NaturalLanguageProcessing": {},
            "ComputerVision": {},
            "ReinforcementLearning": {},
            "GenerativeAI": {},
            "LargeLanguageModels": {},
            "AIEthics": {},
        },
        "SoftwareEngineering": {
            "WebDevelopment": {},
            "MobileDevelopment": {},
            "DevOps": {},
            "SystemDesign": {},
            "DataEngineering": {},
            "Security": {},
            "OpenSource": {},
            "APIs": {},
        },
        "Hardware": {
            "Semiconductors": {},
            "EmbeddedSystems": {},
            "Computers": {},
        },
        "CloudComputing": {},
        "Blockchain": {},
        "Robotics": {},
        "Cybersecurity": {},
        "DataScience": {},
    },
    "Science": {
        "Physics": {},
        "Chemistry": {},
        "Biology": {
            "Genetics": {},
            "Neuroscience": {},
            "Ecology": {},
        },
        "Mathematics": {
            "Statistics": {},
            "LinearAlgebra": {},
            "Calculus": {},
        },
        "SpaceExploration": {},
        "ClimateScience": {},
        "Medicine": {
            "Pharmacology": {},
            "Surgery": {},
            "PublicHealth": {},
        },
        "Psychology": {},
    },
    "Business": {
        "Entrepreneurship": {
            "Startups": {},
            "VentureCapital": {},
            "Fundraising": {},
        },
        "Finance": {
            "Investing": {},
            "PersonalFinance": {},
            "Cryptocurrency": {},
            "StockMarket": {},
        },
        "Marketing": {
            "SocialMedia": {},
            "SEO": {},
            "ContentMarketing": {},
        },
        "Strategy": {},
        "Leadership": {},
        "Economics": {
            "Macroeconomics": {},
            "Microeconomics": {},
        },
        "ProductManagement": {},
        "HumanResources": {},
    },
    "Arts": {
        "Music": {
            "MusicTheory": {},
            "Production": {},
            "MusicHistory": {},
            "Instruments": {},
        },
        "Film": {
            "Cinematography": {},
            "FilmReview": {},
            "Documentary": {},
        },
        "Photography": {},
        "Design": {
            "GraphicDesign": {},
            "UXDesign": {},
            "Architecture": {},
            "InteriorDesign": {},
            "FashionDesign": {},
        },
        "Literature": {},
        "VisualArts": {
            "Painting": {},
            "Sculpture": {},
            "DigitalArt": {},
        },
        "PerformingArts": {
            "Theatre": {},
            "Dance": {},
        },
        "History": {
            "AncientHistory": {},
            "ModernHistory": {},
            "ArtHistory": {},
        },
    },
    "Education": {
        "OnlineLearning": {},
        "Languages": {},
        "Philosophy": {},
        "SelfImprovement": {
            "Productivity": {},
            "Mindset": {},
            "Communication": {},
        },
        "AcademicResearch": {},
        "TutorialAndHowTo": {},
    },
    "Entertainment": {
        "Gaming": {
            "Esports": {},
            "GameReview": {},
            "GameDevelopment": {},
            "GameplayWalkthrough": {},
        },
        "Sports": {
            "Football": {},
            "Basketball": {},
            "Soccer": {},
            "MartialArts": {},
            "Fitness": {},
        },
        "Humor": {},
        "Travel": {},
        "Lifestyle": {
            "Food": {},
            "Fashion": {},
            "HomeAndGarden": {},
        },
        "PopCulture": {},
        "Podcast": {},
    },
    "Politics": {
        "InternationalRelations": {},
        "Policy": {},
        "Activism": {},
        "PoliticalPhilosophy": {},
    },
    "Health": {
        "MentalHealth": {},
        "Nutrition": {},
        "Fitness": {},
        "Medicine": {},
        "Wellness": {},
    },
    "Environment": {
        "ClimateChange": {},
        "Sustainability": {},
        "Wildlife": {},
        "Conservation": {},
    },
    "Other": {
        "Uncategorized": {},
        "Miscellaneous": {},
        "Regional": {},      # locale/country-specific content
        "Shortform": {},     # YouTube Shorts or <2 min clips
        "LiveStream": {},
    },
}


# ---------------------------------------------------------------------------
# Derived flat set — every valid tag at every hierarchy level
# e.g. "Technology", "Technology/ArtificialIntelligence", "Technology/ArtificialIntelligence/MachineLearning"
# ---------------------------------------------------------------------------

def _flatten(tree: dict, prefix: str = "") -> Set[str]:
    result: Set[str] = set()
    for key, subtree in tree.items():
        full = f"{prefix}/{key}" if prefix else key
        result.add(full)
        if subtree:
            result = result | _flatten(subtree, full)
    return result


TAXONOMY_FLAT: Set[str] = _flatten(TAXONOMY_TREE)

# Map lowercase -> canonical for fast lookup
_LOWER_MAP: Dict[str, str] = {t.lower(): t for t in TAXONOMY_FLAT}

# Compact hint for Gemini prompts (top-level + second-level only)
TAXONOMY_HINT: str = ", ".join(sorted(
    t for t in TAXONOMY_FLAT
    if t.count("/") <= 1
))


# ---------------------------------------------------------------------------
# CamelCase helpers
# ---------------------------------------------------------------------------

def _to_camel(s: str) -> str:
    """Convert a raw string token to CamelCase (e.g. 'machine learning' → 'MachineLearning')."""
    # Split on common delimiters
    words = re.split(r"[\s_\-]+", s.strip())
    return "".join((w[0].upper() + w[1:]) for w in words if w)


def _camel_path(raw: str) -> str:
    """Convert a slash-delimited path to CamelCase segments, e.g. 'tech/ai/ml' → 'Technology/ArtificialIntelligence/MachineLearning' (best effort)."""
    segments = [_to_camel(seg) for seg in raw.split("/") if seg]
    return "/".join(segments)


# ---------------------------------------------------------------------------
# Tag validation and normalization
# ---------------------------------------------------------------------------

def _best_match(candidate: str) -> str | None:
    """
    Try to resolve a raw candidate tag to a known taxonomy entry.
    Strategy (in order):
      1. Exact match (case-insensitive)
      2. CamelCase the candidate and try again
      3. Match on any trailing segment (e.g. "MachineLearning" → "Technology/ArtificialIntelligence/MachineLearning")
    Returns the canonical tag or None.
    """
    lower = candidate.lower()
    if lower in _LOWER_MAP:
        return _LOWER_MAP[lower]

    camel = _camel_path(candidate)
    camel_lower = camel.lower()
    if camel_lower in _LOWER_MAP:
        return _LOWER_MAP[camel_lower]

    # Try matching just the last segment against all known leaves
    leaf = camel.split("/")[-1].lower()
    matches = [t for t in TAXONOMY_FLAT if t.split("/")[-1].lower() == leaf]
    if len(matches) == 1:
        return matches[0]

    return None

def _is_dynamic_entity(candidate: str) -> Optional[str]:
    """
    Check if the tag starts with an allowed dynamic prefix.
    Returns the canonical tag if valid, or None.
    Handles both:
      - "Person/ElonMusk"  -> "Person/ElonMusk"  (full entity)
      - "Person"           -> "Person"            (bare root, used as parent node)
    """
    candidate_lower = candidate.lower()

    # Check bare root (e.g. "Person", "Company") — valid as a parent-level node
    for prefix in DYNAMIC_PREFIXES:
        root = prefix.rstrip("/")
        if candidate_lower == root.lower():
            return root  # Return the canonical root name

    # Check prefixed entity (e.g. "Person/ElonMusk")
    for prefix in DYNAMIC_PREFIXES:
        if candidate_lower.startswith(prefix.lower()):
            entity_raw = candidate[len(prefix):]
            entity_camel = _to_camel(entity_raw)
            if entity_camel:
                return f"{prefix}{entity_camel}"
            return None

    return None


def _expand_ancestors(tag: str) -> List[str]:
    """Given 'Technology/ArtificialIntelligence/MachineLearning' return all ancestor tags too."""
    parts = tag.split("/")
    return ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def normalize_tags(raw: List[str]) -> List[str]:
    """
    Convert a list of raw Gemini-generated tag strings into a clean, validated,
    deduplicated, ancestor-expanded list of taxonomy tags.

    Rules:
    - Each raw tag is matched against TAXONOMY_FLAT (case-insensitive + CamelCase coercion)
    - Matched tags are expanded to include all ancestor levels
    - Tags starting with special prefixes (Person/, Company/, etc.) are dynamically accepted
    - Unrecognized tags → 'Other/Uncategorized' (never silently dropped)
    - Result is deduplicated and sorted: parents before children, then alphabetically

    Returns:
        List of canonical taxonomy tag strings.
    """
    resolved: Set[str] = set()
    had_unknown = False

    for raw_tag in raw:
        # Strip only truly unsafe chars — preserve Unicode letters/digits (CJK, Latin, etc.)
        cleaned = re.sub(r"[^\w/\- ]", "", raw_tag, flags=re.UNICODE).strip()
        if not cleaned:
            had_unknown = True
            continue

        match = _best_match(cleaned)
        if match:
            for ancestor in _expand_ancestors(match):
                resolved.add(ancestor)
            continue
            
        dynamic_tag = _is_dynamic_entity(cleaned)
        if dynamic_tag:
            # Add the prefix itself (e.g. "Person"), then the full tag
            prefix_only = dynamic_tag.split("/")[0]
            resolved.add(prefix_only)
            resolved.add(dynamic_tag)
            continue

        print(f"  [taxonomy] No match for '{raw_tag}' → Other/Uncategorized")
        had_unknown = True

    if had_unknown or not resolved:
        resolved.add("Other")
        resolved.add("Other/Uncategorized")

    # Sort: by depth (parent first), then alphabetically within same depth
    return sorted(resolved, key=lambda t: (t.count("/"), t))
