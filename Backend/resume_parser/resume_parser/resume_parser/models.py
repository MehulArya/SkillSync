"""
models.py
=========
Shared data models for the resume parsing system.

These dataclasses are the *single contract* between the CommonParser and every
downstream consumer (ATSOutputBuilder, InterviewOutputBuilder, etc). Nothing
outside `parser/` should ever touch raw PDF/text/regex internals — everyone
else only ever sees `ParsedResume`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContactInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


@dataclass
class Education:
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    raw_text: str = ""


@dataclass
class Experience:
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    bullets: List[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class Project:
    name: Optional[str] = None
    description: str = ""
    technologies: List[str] = field(default_factory=list)
    bullets: List[str] = field(default_factory=list)
    link: Optional[str] = None
    raw_text: str = ""


@dataclass
class Certification:
    name: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None
    raw_text: str = ""


@dataclass
class Skill:
    name: str
    category: Optional[str] = None  # e.g. "language", "framework", "tool", "soft"


@dataclass
class ParsedResume:
    """
    Complete structured resume data extracted ONCE by CommonParser.
    Every output transformer (ATS / Interview) is built from this object only.
    """

    contact: ContactInfo = field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: List[Skill] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    certifications: List[Certification] = field(default_factory=list)

    # Section-detection metadata (useful for debugging / re-parsing)
    raw_text: str = ""
    detected_sections: dict = field(default_factory=dict)

    def skill_names(self) -> List[str]:
        return [s.name for s in self.skills]
