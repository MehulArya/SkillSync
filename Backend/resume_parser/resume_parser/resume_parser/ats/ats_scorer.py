"""
ats_scorer.py
=============
ATSScorer: combines ATSResumeData (from outputs/ats_output.py) with a job
description to produce a score, matched/missing skills, and suggestions.

This module owns ALL job-description-aware logic. It never touches PDF
parsing or section detection directly — it only consumes the already-built
ATSResumeData.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from ..outputs.ats_output import ATSResumeData

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}")

# Small stoplist so common English words in the JD don't get treated as
# "required skills". Not exhaustive by design — good enough for keyword
# matching without pulling in a full NLP dependency here.
_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "who", "job", "role", "team", "work", "years",
    "experience", "strong", "ability", "excellent", "including", "using",
    "etc", "plus", "must", "should", "can", "into", "such", "some", "any",
    "all", "not", "but", "than", "then", "they", "them", "their", "have",
    "has", "had", "been", "being", "over", "under", "per", "via", "within",
    "hiring", "build", "building", "machine", "learning", "engineer",
    "requirements", "responsibilities", "we", "you'll", "looking",
}


@dataclass
class ATSScoreResult:
    score: float  # 0-100
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    keyword_coverage: float = 0.0  # fraction of JD keywords found anywhere in resume text
    suggestions: List[str] = field(default_factory=list)


class ATSScorer:
    """
    Stateless scorer. score() is the main entry point.

    Scoring weights (kept simple + explainable, easy to tune later):
        - 70% skill-list overlap (JD-implied skills vs resume skills)
        - 30% general keyword coverage (JD tokens found anywhere in resume text)
    """

    SKILL_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3

    def score(self, ats_data: ATSResumeData, job_description: str) -> ATSScoreResult:
        jd_keywords = self._extract_keywords(job_description)
        jd_skills = self._extract_candidate_skills(job_description)

        resume_skill_set = set(ats_data.normalized_skills)

        matched = sorted(s for s in jd_skills if s in resume_skill_set)
        missing = sorted(s for s in jd_skills if s not in resume_skill_set)

        skill_score = (len(matched) / len(jd_skills)) if jd_skills else 1.0

        keyword_hits = sum(1 for kw in jd_keywords if kw in ats_data.searchable_text)
        keyword_coverage = (keyword_hits / len(jd_keywords)) if jd_keywords else 1.0

        overall = (skill_score * self.SKILL_WEIGHT + keyword_coverage * self.KEYWORD_WEIGHT) * 100

        suggestions = self._build_suggestions(ats_data, missing, keyword_coverage)

        return ATSScoreResult(
            score=round(overall, 1),
            matched_skills=matched,
            missing_skills=missing,
            keyword_coverage=round(keyword_coverage, 3),
            suggestions=suggestions,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        words = [w.lower() for w in _WORD_RE.findall(text)]
        return sorted({w for w in words if len(w) > 2 and w not in _STOPWORDS})

    @staticmethod
    def _extract_candidate_skills(job_description: str) -> List[str]:
        """
        Heuristic: pull comma/bullet separated tokens out of a "requirements"
        or "skills" style line, plus any capitalized tech-looking tokens.
        In a production system this would call the AI/ML services layer
        (embeddings / LLM) for JD skill extraction — this module keeps a
        deterministic regex fallback so ATS scoring never hard-depends on an
        external LLM call.
        """
        candidates = set()

        # Primary signal: explicit "Skills:"/"Requirements:"/"Stack:" lines —
        # comma/bullet separated tokens there are almost always genuine
        # skill names, including multi-word ones ("Machine Learning").
        for line in job_description.splitlines():
            if re.search(r"(skills?|requirements?|stack|technologies)\s*[:\-]", line, re.I):
                _, _, rest = line.partition(":")
                rest = rest or line
                for chunk in re.split(r"[,•\u2022;/]+", rest):
                    token = chunk.strip(" .")
                    if token and len(token) < 30 and token.lower() not in _STOPWORDS:
                        candidates.add(token.lower())

        # Secondary signal: capitalized tech-looking tokens found anywhere,
        # EXCLUDING words that merely start a sentence (those are usually
        # ordinary English, e.g. "We", "Requirements", "Machine ..." at a
        # line's start) unless they look like an acronym/product name
        # (contain a digit/symbol, are all-uppercase, or are mixed-case like
        # "TensorFlow"/"React.js").
        sentence_start_positions = {0}
        for m in re.finditer(r"[.\n]\s*", job_description):
            sentence_start_positions.add(m.end())

        for m in re.finditer(r"\b[A-Z][A-Za-z0-9+#.]{1,20}\b", job_description):
            token = m.group(0)
            lower = token.lower()
            if lower in _STOPWORDS:
                continue
            looks_like_acronym_or_product = (
                token.isupper()
                or any(c.isdigit() or c in "+#." for c in token)
                or (not token.islower() and not token.istitle())  # mixed case, e.g. TensorFlow
            )
            if m.start() in sentence_start_positions and not looks_like_acronym_or_product:
                continue
            candidates.add(lower)

        return sorted(candidates)

    @staticmethod
    def _build_suggestions(
        ats_data: ATSResumeData, missing_skills: List[str], keyword_coverage: float
    ) -> List[str]:
        suggestions = []

        if missing_skills:
            top_missing = ", ".join(missing_skills[:8])
            suggestions.append(
                f"Add or highlight these JD-relevant skills if you genuinely have them: {top_missing}"
            )

        if not ats_data.experience_bullets:
            suggestions.append("Add quantified bullet points under work experience (metrics, impact, scale).")

        if keyword_coverage < 0.5:
            suggestions.append(
                "Overall keyword overlap with the job description is low — mirror the JD's terminology "
                "where accurate (e.g. exact tool/framework names)."
            )

        if not ats_data.certifications:
            suggestions.append("Consider adding relevant certifications if you have any, ATS systems often weight these.")

        if not suggestions:
            suggestions.append("Strong match — resume already covers most JD-relevant skills and keywords.")

        return suggestions
