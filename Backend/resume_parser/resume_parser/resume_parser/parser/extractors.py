"""
extractors.py
=============
Pure extraction functions: given a section's raw text (+ optionally a spaCy
Doc), return structured objects. No PDF/IO/orchestration logic lives here —
that stays in common_parser.py. Keeping this separate means ATS/Interview
logic never needs to know regex existed.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import Certification, ContactInfo, Education, Experience, Project, Skill

# ---------------------------------------------------------------------------
# Contact info
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}")
_LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", re.I)
_GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9\-_/]+", re.I)
_URL_RE = re.compile(r"https?://[^\s,)]+", re.I)


def extract_contact_info(header_text: str, nlp=None) -> ContactInfo:
    contact = ContactInfo()

    email_match = _EMAIL_RE.search(header_text)
    if email_match:
        contact.email = email_match.group(0)

    phone_match = _PHONE_RE.search(header_text)
    if phone_match:
        candidate = phone_match.group(0).strip()
        if sum(c.isdigit() for c in candidate) >= 7:  # avoid false positives (years etc.)
            contact.phone = candidate

    li_match = _LINKEDIN_RE.search(header_text)
    if li_match:
        contact.linkedin = li_match.group(0)

    gh_match = _GITHUB_RE.search(header_text)
    if gh_match:
        contact.github = gh_match.group(0)

    other_urls = [
        u for u in _URL_RE.findall(header_text) if "linkedin" not in u and "github" not in u
    ]
    if other_urls:
        contact.portfolio = other_urls[0]

    # Name: prefer spaCy NER (PERSON) on the first few lines; fall back to
    # "first non-empty line that isn't an email/phone/url".
    first_lines = [l.strip() for l in header_text.splitlines() if l.strip()][:5]
    if nlp is not None and first_lines:
        doc = nlp("\n".join(first_lines))
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            contact.name = persons[0]

    if not contact.name and first_lines:
        for line in first_lines:
            if _EMAIL_RE.search(line) or _PHONE_RE.search(line) or _URL_RE.search(line):
                continue
            contact.name = line
            break

    # Location heuristic: a short line containing a comma near the top,
    # not already claimed as name/contact fields.
    for line in first_lines:
        if line == contact.name:
            continue
        if "," in line and len(line) < 60 and not _EMAIL_RE.search(line):
            contact.location = line
            break

    return contact


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_SKILL_SPLIT_RE = re.compile(r"[,•|\u2022\n/;]+")


def extract_skills(skills_text: str) -> List[Skill]:
    skills: List[Skill] = []
    seen = set()
    for chunk in _SKILL_SPLIT_RE.split(skills_text):
        name = chunk.strip(" -\t")
        # Drop category labels like "Languages:" that precede a colon list.
        if ":" in name:
            _, name = name.split(":", 1)
            name = name.strip()
        if not name or len(name) > 40:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(Skill(name=name))
    return skills


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

_DATE_RANGE_RE = re.compile(
    r"(\b(?:19|20)\d{2}\b|\b[A-Za-z]{3,9}\.?\s+(?:19|20)\d{2}\b)"
    r"\s*(?:-|–|to)\s*"
    r"(\b(?:19|20)\d{2}\b|\b[A-Za-z]{3,9}\.?\s+(?:19|20)\d{2}\b|present|current)",
    re.I,
)
_GPA_RE = re.compile(r"(?:cgpa|gpa)\s*[:\-]?\s*([\d.]+\s*/?\s*[\d.]*)", re.I)
_DEGREE_RE = re.compile(
    r"(B\.?\s?Tech|M\.?\s?Tech|B\.?\s?E\.?|M\.?\s?E\.?|B\.?Sc|M\.?Sc|Ph\.?D|MBA|BBA|Bachelor(?:'?s)?|Master(?:'?s)?)"
    r"[^\n,]*",
    re.I,
)


def extract_education(education_text: str) -> List[Education]:
    entries: List[Education] = []
    blocks = [b.strip() for b in re.split(r"\n{2,}", education_text) if b.strip()]
    if len(blocks) <= 1:
        # Fall back to splitting by lines that look like a new institution
        # (heuristic: line count is small enough this is fine either way).
        blocks = [b.strip() for b in education_text.split("\n") if b.strip()]
        blocks = ["\n".join(blocks)] if blocks else []

    for block in blocks:
        edu = Education(raw_text=block)
        date_match = _DATE_RANGE_RE.search(block)
        if date_match:
            edu.start_date, edu.end_date = date_match.group(1), date_match.group(2)
        gpa_match = _GPA_RE.search(block)
        if gpa_match:
            edu.gpa = gpa_match.group(1).strip()
        degree_match = _DEGREE_RE.search(block)
        if degree_match:
            edu.degree = degree_match.group(0).strip(" ,.")
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if lines:
            edu.institution = lines[0]
        entries.append(edu)

    return entries


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


def extract_experience(experience_text: str) -> List[Experience]:
    entries: List[Experience] = []
    blocks = [b.strip() for b in re.split(r"\n{2,}", experience_text) if b.strip()]
    if len(blocks) <= 1 and experience_text.strip():
        blocks = [experience_text.strip()]

    for block in blocks:
        exp = Experience(raw_text=block)
        date_match = _DATE_RANGE_RE.search(block)
        if date_match:
            exp.start_date, exp.end_date = date_match.group(1), date_match.group(2)

        lines = [l.strip() for l in block.splitlines() if l.strip()]
        bullets, header_lines = [], []
        for line in lines:
            if line.startswith(("-", "•", "*", "\u2022")):
                bullets.append(line.lstrip("-•*\u2022 ").strip())
            else:
                header_lines.append(line)

        if header_lines:
            # Common pattern: "Title, Company" or "Company | Title"
            first = header_lines[0]
            for sep in ["|", " at ", ","]:
                if sep in first:
                    parts = [p.strip() for p in first.split(sep, 1)]
                    exp.title, exp.company = parts[0], parts[1]
                    break
            else:
                exp.title = first
            if len(header_lines) > 1:
                exp.location = header_lines[1]

        exp.bullets = bullets
        entries.append(exp)

    return entries


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

_TECH_LINE_RE = re.compile(r"(?:tech(?:nologies)?|stack|tools?)\s*[:\-]\s*(.+)", re.I)


def extract_projects(projects_text: str) -> List[Project]:
    entries: List[Project] = []
    blocks = [b.strip() for b in re.split(r"\n{2,}", projects_text) if b.strip()]
    if len(blocks) <= 1 and projects_text.strip():
        blocks = [projects_text.strip()]

    for block in blocks:
        proj = Project(raw_text=block)
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        bullets, desc_lines = [], []

        for line in lines:
            tech_match = _TECH_LINE_RE.search(line)
            if tech_match:
                proj.technologies = [t.strip() for t in _SKILL_SPLIT_RE.split(tech_match.group(1)) if t.strip()]
                continue
            if line.startswith(("-", "•", "*", "\u2022")):
                bullets.append(line.lstrip("-•*\u2022 ").strip())
            else:
                desc_lines.append(line)

        url_match = _URL_RE.search(block)
        if url_match:
            proj.link = url_match.group(0)

        if desc_lines:
            proj.name = desc_lines[0]
            proj.description = " ".join(desc_lines[1:])
        proj.bullets = bullets
        entries.append(proj)

    return entries


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


def extract_certifications(cert_text: str) -> List[Certification]:
    entries: List[Certification] = []
    lines = [l.strip(" -•\u2022\t") for l in cert_text.splitlines() if l.strip()]
    for line in lines:
        cert = Certification(raw_text=line)
        date_match = re.search(r"\b(19|20)\d{2}\b", line)
        if date_match:
            cert.date = date_match.group(0)
        if "-" in line or "|" in line:
            sep = "-" if "-" in line else "|"
            parts = [p.strip() for p in line.split(sep, 1)]
            cert.name, cert.issuer = parts[0], parts[1]
        else:
            cert.name = line
        entries.append(cert)
    return entries


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def extract_summary(summary_text: str) -> Optional[str]:
    text = summary_text.strip()
    return text or None
