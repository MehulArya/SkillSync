"""
section_detector.py
====================
Splits raw resume text into labeled sections (SUMMARY, SKILLS, EDUCATION,
EXPERIENCE, PROJECTS, CERTIFICATIONS) using header-line heuristics.

This is intentionally isolated from extraction logic (extractors.py) so the
"where does a section start/end" concern never mixes with the "what fields
live inside this section" concern.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Canonical section -> header aliases that show up on real resumes.
SECTION_ALIASES: Dict[str, List[str]] = {
    "summary": ["summary", "objective", "profile", "about me", "career objective"],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "skill set",
        "technologies",
    ],
    "education": ["education", "academic background", "academics", "qualification"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internships",
        "internship experience",
    ],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "certifications": [
        "certifications",
        "certificates",
        "licenses & certifications",
        "courses & certifications",
    ],
}

_HEADER_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z &/]{1,40}$")


def _normalize(line: str) -> str:
    return re.sub(r"[^a-z& ]", "", line.strip().lower())


def _match_section(line: str) -> str | None:
    norm = _normalize(line)
    if not norm:
        return None
    for canonical, aliases in SECTION_ALIASES.items():
        if norm in aliases:
            return canonical
    return None


def detect_sections(text: str) -> Dict[str, str]:
    """
    Returns {canonical_section_name: section_body_text}.
    Any text before the first detected header is bucketed as 'header' (name/
    contact block usually lives there).
    """
    lines = text.splitlines()
    boundaries: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 45:
            continue
        # Headers are typically short, standalone lines (often ALL CAPS or
        # Title Case) that match a known alias.
        looks_like_header = stripped.isupper() or _HEADER_LINE_RE.match(stripped)
        if looks_like_header:
            section = _match_section(stripped)
            if section:
                boundaries.append((idx, section))

    sections: Dict[str, str] = {}
    if not boundaries:
        sections["header"] = text
        return sections

    sections["header"] = "\n".join(lines[: boundaries[0][0]]).strip()

    for i, (start_idx, name) in enumerate(boundaries):
        end_idx = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[start_idx + 1 : end_idx]).strip()
        # If the same section header appears twice, merge bodies rather than
        # silently overwrite (some resumes split "Technical Skills" across
        # two visual columns extracted as separate blocks).
        if name in sections:
            sections[name] = sections[name] + "\n" + body
        else:
            sections[name] = body

    return sections
