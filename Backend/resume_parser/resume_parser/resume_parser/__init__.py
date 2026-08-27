"""
resume_parser
=============
Reusable resume parsing system: parse a resume PDF exactly once, then derive
either ATS scoring output or interview-question output from the same parsed
data.

Typical usage:

    from resume_parser import ResumePipeline

    pipeline = ResumePipeline()
    pipeline.load(pdf_path="resume.pdf")

    ats_result = pipeline.run_ats(job_description=jd_text)
    interview_result = pipeline.run_interview()
"""

from .models import (
    Certification,
    ContactInfo,
    Education,
    Experience,
    ParsedResume,
    Project,
    Skill,
)
from .pipeline import ATSResult, InterviewResult, ResumePipeline

__all__ = [
    "ResumePipeline",
    "ATSResult",
    "InterviewResult",
    "ParsedResume",
    "ContactInfo",
    "Education",
    "Experience",
    "Project",
    "Certification",
    "Skill",
]
