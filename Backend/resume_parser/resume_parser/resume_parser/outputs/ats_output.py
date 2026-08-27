"""
ats_output.py
=============
ATSOutputBuilder: pure transformation of ParsedResume -> ATS-shaped data.

It does NOT compute a score and does NOT know about a job description —
that's ats/ats_scorer.py's job. This module only reshapes/normalizes the
already-parsed resume into the flat, keyword-friendly structure ATS scoring
needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..models import ParsedResume


@dataclass
class ATSResumeData:
    """Flattened, keyword-oriented view of a resume for ATS matching."""

    full_name: str = ""
    email: str = ""
    phone: str = ""

    all_skills: List[str] = field(default_factory=list)
    normalized_skills: List[str] = field(default_factory=list)  # lowercased, deduped

    job_titles: List[str] = field(default_factory=list)
    companies: List[str] = field(default_factory=list)
    experience_bullets: List[str] = field(default_factory=list)
    total_experience_entries: int = 0

    degrees: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)

    project_names: List[str] = field(default_factory=list)
    project_technologies: List[str] = field(default_factory=list)

    certifications: List[str] = field(default_factory=list)

    # Single searchable blob used for keyword-presence checks against a JD.
    searchable_text: str = ""


class ATSOutputBuilder:
    """
    Builds an ATSResumeData from a ParsedResume. Stateless — safe to reuse
    across requests.
    """

    def build(self, resume: ParsedResume) -> ATSResumeData:
        skills = resume.skill_names()

        experience_bullets = [b for exp in resume.experience for b in exp.bullets]
        job_titles = [exp.title for exp in resume.experience if exp.title]
        companies = [exp.company for exp in resume.experience if exp.company]

        degrees = [edu.degree for edu in resume.education if edu.degree]
        institutions = [edu.institution for edu in resume.education if edu.institution]

        project_names = [p.name for p in resume.projects if p.name]
        project_technologies = sorted({t for p in resume.projects for t in p.technologies})

        certifications = [c.name for c in resume.certifications if c.name]

        searchable_parts = [
            resume.summary or "",
            " ".join(skills),
            " ".join(experience_bullets),
            " ".join(job_titles),
            " ".join(p.description for p in resume.projects),
            " ".join(project_technologies),
            " ".join(certifications),
        ]

        return ATSResumeData(
            full_name=resume.contact.name or "",
            email=resume.contact.email or "",
            phone=resume.contact.phone or "",
            all_skills=skills,
            normalized_skills=sorted({s.lower().strip() for s in skills if s.strip()}),
            job_titles=job_titles,
            companies=companies,
            experience_bullets=experience_bullets,
            total_experience_entries=len(resume.experience),
            degrees=degrees,
            institutions=institutions,
            project_names=project_names,
            project_technologies=project_technologies,
            certifications=certifications,
            searchable_text=" \n".join(p for p in searchable_parts if p).lower(),
        )
