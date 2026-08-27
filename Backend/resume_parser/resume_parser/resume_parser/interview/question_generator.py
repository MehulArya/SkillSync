"""
question_generator.py
======================
InterviewQuestionGenerator: turns InterviewResumeData (from
outputs/interview_output.py) into interview questions + follow-up questions.

Owns ALL interview-specific logic. Never touches ATS scoring or PDF parsing.
The template-based generation below is a deterministic fallback; swap
`_llm_generate()` in for a real call into the AI/ML services layer (LLM
service) without changing this class's public interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..outputs.interview_output import InterviewResumeData


@dataclass
class InterviewQuestion:
    topic: str  # "skills" | "projects" | "experience" | "education" | "certifications"
    question: str
    follow_ups: List[str] = field(default_factory=list)


@dataclass
class InterviewQuestionSet:
    candidate_name: str
    questions: List[InterviewQuestion] = field(default_factory=list)


class InterviewQuestionGenerator:
    """
    Stateless generator. generate() is the main entry point.

    max_per_category caps how many questions are produced per resume section
    so the interview stays a reasonable length.
    """

    def __init__(self, max_per_category: int = 3):
        self.max_per_category = max_per_category

    def generate(self, data: InterviewResumeData) -> InterviewQuestionSet:
        questions: List[InterviewQuestion] = []

        questions.extend(self._skill_questions(data))
        questions.extend(self._project_questions(data))
        questions.extend(self._experience_questions(data))
        questions.extend(self._education_questions(data))
        questions.extend(self._certification_questions(data))

        return InterviewQuestionSet(candidate_name=data.candidate_name, questions=questions)

    def generate_followups(self, question: InterviewQuestion, candidate_answer: str) -> List[str]:
        """
        Adaptive follow-up generation based on the candidate's answer.
        Deterministic heuristic fallback: if the answer is short/vague, probe
        deeper; otherwise probe for edge cases and trade-offs. Swap this
        method's body for an LLM call for real adaptive behaviour.
        """
        followups = list(question.follow_ups)
        word_count = len(candidate_answer.split())

        if word_count < 15:
            followups.insert(0, "Could you walk me through that in more detail with a concrete example?")
        else:
            followups.append("What was the most challenging trade-off you had to make there, and why?")

        return followups

    # ------------------------------------------------------------------
    # Category-specific generators
    # ------------------------------------------------------------------

    def _skill_questions(self, data: InterviewResumeData) -> List[InterviewQuestion]:
        out = []
        for skill in data.skills[: self.max_per_category]:
            out.append(
                InterviewQuestion(
                    topic="skills",
                    question=f"Tell me about a time you used {skill.name} to solve a real problem.",
                    follow_ups=[
                        f"What alternatives to {skill.name} did you consider, and why did you pick it?",
                        f"What's a limitation of {skill.name} you've run into?",
                    ],
                )
            )
        return out

    def _project_questions(self, data: InterviewResumeData) -> List[InterviewQuestion]:
        out = []
        for project in data.projects[: self.max_per_category]:
            tech = ", ".join(project.technologies) if project.technologies else "the tools you chose"
            out.append(
                InterviewQuestion(
                    topic="projects",
                    question=f"Walk me through the '{project.name}' project — what problem did it solve and what was your role?",
                    follow_ups=[
                        f"Why did you choose {tech} for this?",
                        "What would you do differently if you rebuilt it today?",
                        "What was the hardest bug or design decision in this project?",
                    ],
                )
            )
        return out

    def _experience_questions(self, data: InterviewResumeData) -> List[InterviewQuestion]:
        out = []
        for exp in data.experience[: self.max_per_category]:
            role = f"{exp.title} at {exp.company}" if exp.company else exp.title
            out.append(
                InterviewQuestion(
                    topic="experience",
                    question=f"As {role}, what was the most impactful thing you shipped or improved?",
                    follow_ups=[
                        "How did you measure that impact?",
                        "Who did you have to collaborate with, and what was tricky about that?",
                    ],
                )
            )
        return out

    def _education_questions(self, data: InterviewResumeData) -> List[InterviewQuestion]:
        out = []
        for edu in data.education[: self.max_per_category]:
            if not edu.degree:
                continue
            out.append(
                InterviewQuestion(
                    topic="education",
                    question=f"What in your {edu.degree} coursework at {edu.institution} do you draw on most in practice?",
                    follow_ups=["Was there a course project you're particularly proud of?"],
                )
            )
        return out

    def _certification_questions(self, data: InterviewResumeData) -> List[InterviewQuestion]:
        out = []
        for cert in data.certifications[: self.max_per_category]:
            if not cert.name:
                continue
            out.append(
                InterviewQuestion(
                    topic="certifications",
                    question=f"What motivated you to pursue the {cert.name} certification, and how have you applied it?",
                    follow_ups=["What was the most useful thing you learned getting certified?"],
                )
            )
        return out
