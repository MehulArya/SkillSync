"""
interview_output.py
====================
InterviewOutputBuilder: pure transformation of ParsedResume -> interview-
shaped data. No question generation here — that lives in
interview/question_generator.py. This module's only job is to package the
already-parsed resume into the shape the interview engine expects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..models import ParsedResume


@dataclass
class InterviewSkillTopic:
    name: str
    category: str | None = None


@dataclass
class InterviewProjectTopic:
    name: str
    description: str
    technologies: List[str] = field(default_factory=list)
    talking_points: List[str] = field(default_factory=list)  # bullets, good for "walk me through X"


@dataclass
class InterviewExperienceTopic:
    title: str
    company: str
    duration: str
    highlights: List[str] = field(default_factory=list)


@dataclass
class InterviewEducationTopic:
    institution: str
    degree: str
    duration: str


@dataclass
class InterviewCertificationTopic:
    name: str
    issuer: str


@dataclass
class InterviewResumeData:
    """Structured, topic-oriented view of a resume for interview-question generation."""

    candidate_name: str = ""
    summary: str = ""

    skills: List[InterviewSkillTopic] = field(default_factory=list)
    projects: List[InterviewProjectTopic] = field(default_factory=list)
    experience: List[InterviewExperienceTopic] = field(default_factory=list)
    education: List[InterviewEducationTopic] = field(default_factory=list)
    certifications: List[InterviewCertificationTopic] = field(default_factory=list)


class InterviewOutputBuilder:
    """
    Builds an InterviewResumeData from a ParsedResume. Stateless — safe to
    reuse across requests.
    """

    def build(self, resume: ParsedResume) -> InterviewResumeData:
        skills = [InterviewSkillTopic(name=s.name, category=s.category) for s in resume.skills]

        projects = [
            InterviewProjectTopic(
                name=p.name or "Untitled project",
                description=p.description,
                technologies=p.technologies,
                talking_points=p.bullets,
            )
            for p in resume.projects
        ]

        experience = [
            InterviewExperienceTopic(
                title=exp.title or "",
                company=exp.company or "",
                duration=self._format_duration(exp.start_date, exp.end_date),
                highlights=exp.bullets,
            )
            for exp in resume.experience
        ]

        education = [
            InterviewEducationTopic(
                institution=edu.institution or "",
                degree=edu.degree or "",
                duration=self._format_duration(edu.start_date, edu.end_date),
            )
            for edu in resume.education
        ]

        certifications = [
            InterviewCertificationTopic(name=c.name or "", issuer=c.issuer or "")
            for c in resume.certifications
        ]

        return InterviewResumeData(
            candidate_name=resume.contact.name or "",
            summary=resume.summary or "",
            skills=skills,
            projects=projects,
            experience=experience,
            education=education,
            certifications=certifications,
        )

    @staticmethod
    def _format_duration(start: str | None, end: str | None) -> str:
        if start and end:
            return f"{start} - {end}"
        return start or end or ""
