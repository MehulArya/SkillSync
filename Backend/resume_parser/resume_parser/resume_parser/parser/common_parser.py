"""
common_parser.py
=================
CommonResumeParser — THE single place PDF bytes become a ParsedResume.

Design intent (matches the required flow):

    Resume PDF -> CommonParser (PyMuPDF + spaCy + regex + section detection)
              -> ParsedResume (complete structured data, extracted ONCE)

Both ATSOutputBuilder and InterviewOutputBuilder consume the same
ParsedResume instance. Nothing about ATS scoring or interview-question
generation is allowed to leak into this file, and this file never imports
from `ats/` or `interview/`.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..models import ParsedResume
from . import extractors
from .section_detector import detect_sections

logger = logging.getLogger(__name__)


class CommonResumeParser:
    """
    Reusable, stateless-per-call parser.

    Usage:
        parser = CommonResumeParser()
        parsed = parser.parse(pdf_path="resume.pdf")
        # or: parser.parse(pdf_bytes=uploaded_file.read())
        # or: parser.parse(text=already_extracted_text)
    """

    def __init__(self, spacy_model: str = "en_core_web_sm", load_spacy: bool = True):
        self._nlp = None
        if load_spacy:
            self._nlp = self._load_spacy(spacy_model)

    @staticmethod
    def _load_spacy(model_name: str):
        try:
            import spacy

            return spacy.load(model_name)
        except Exception as exc:  # model missing / spaCy not installed
            logger.warning(
                "spaCy model '%s' unavailable (%s) — falling back to regex-only "
                "extraction for name detection.",
                model_name,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_from_pdf(pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> str:
        import fitz  # PyMuPDF

        if pdf_path:
            doc = fitz.open(pdf_path)
        elif pdf_bytes:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            raise ValueError("Either pdf_path or pdf_bytes must be provided")

        pages_text = []
        for page in doc:
            # "text" layout preserves reading order reasonably well for
            # single/double-column resumes; sorted for extra stability.
            pages_text.append(page.get_text("text", sort=True))
        doc.close()
        return "\n".join(pages_text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        pdf_path: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        text: Optional[str] = None,
    ) -> ParsedResume:
        """
        Parse a resume ONCE into a complete ParsedResume.

        Exactly one of pdf_path / pdf_bytes / text should be provided.
        `text` is exposed mainly for testing without a real PDF file.
        """
        if text is None:
            raw_text = self._extract_text_from_pdf(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
        else:
            raw_text = text

        if not raw_text or not raw_text.strip():
            raise ValueError("No extractable text found in resume")

        sections = detect_sections(raw_text)

        resume = ParsedResume(raw_text=raw_text, detected_sections=sections)

        resume.contact = extractors.extract_contact_info(sections.get("header", ""), nlp=self._nlp)
        resume.summary = extractors.extract_summary(sections.get("summary", ""))
        resume.skills = extractors.extract_skills(sections.get("skills", ""))
        resume.education = extractors.extract_education(sections.get("education", ""))
        resume.experience = extractors.extract_experience(sections.get("experience", ""))
        resume.projects = extractors.extract_projects(sections.get("projects", ""))
        resume.certifications = extractors.extract_certifications(sections.get("certifications", ""))

        return resume
