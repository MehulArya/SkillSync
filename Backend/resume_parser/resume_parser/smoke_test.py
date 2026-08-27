import sys

sys.path.insert(0, ".")

from resume_parser import ResumePipeline

SAMPLE_RESUME_TEXT = """Mukul Raj
mukul.raj@example.com | +91 98765 43210
Jaipur, India | linkedin.com/in/mukulraj | github.com/MukulRaj-704

SUMMARY
Final-year B.Tech CSE student focused on ML and full-stack development.

SKILLS
Python, Java, C++, TensorFlow, Scikit-learn, React.js, Django REST Framework, PostgreSQL, Git, Docker

EDUCATION
Swami Keshvanand Institute of Technology
B.Tech in Computer Science and Engineering
2022 - 2026
CGPA: 9.44/10

EXPERIENCE
Data Science Intern | Celebal Technologies
Jun 2025 - Aug 2025
- Built ensemble learning models improving prediction accuracy by 12%
- Handled large-scale datasets with PySpark pipelines
- Deployed models via Flask REST APIs

PROJECTS
DriveWise
A RAG-based conversational assistant for car brochures using LangChain and FAISS.
Tech: Python, LangChain, FAISS, Streamlit
- Implemented retrieval-augmented generation pipeline
- Reduced query latency by 40% through embedding caching

Jobrix
AI-powered job platform with resume parsing, ATS scoring and AI interviews.
Tech: React.js, Django REST Framework, spaCy, PostgreSQL
- Led AI/LLM development as team lead
- Designed 6-layer system architecture

CERTIFICATIONS
AWS Certified Cloud Practitioner - Amazon Web Services - 2024
Deep Learning Specialization - Coursera - 2023
"""

SAMPLE_JD = """
We are hiring a Machine Learning Engineer.

Requirements: Python, TensorFlow, PyTorch, Django, PostgreSQL, Docker, Kubernetes, AWS

You will build and deploy ML models at scale, working with large datasets and
REST APIs. 2+ years of experience with React is a plus.
"""


def main():
    pipeline = ResumePipeline()
    parsed = pipeline.load(text=SAMPLE_RESUME_TEXT)

    print("=== PARSED (once) ===")
    print("Name:", parsed.contact.name)
    print("Email:", parsed.contact.email)
    print("Phone:", parsed.contact.phone)
    print("GitHub:", parsed.contact.github)
    print("Skills:", parsed.skill_names())
    print("Education entries:", len(parsed.education))
    print("Experience entries:", len(parsed.experience))
    print("Projects:", [p.name for p in parsed.projects])
    print("Certifications:", [c.name for c in parsed.certifications])

    print("\n=== ATS FLOW ===")
    ats_result = pipeline.run_ats(job_description=SAMPLE_JD)
    print("Score:", ats_result.score_result.score)
    print("Matched skills:", ats_result.score_result.matched_skills)
    print("Missing skills:", ats_result.score_result.missing_skills)
    print("Suggestions:", ats_result.score_result.suggestions)

    print("\n=== INTERVIEW FLOW ===")
    interview_result = pipeline.run_interview()
    for q in interview_result.question_set.questions[:6]:
        print(f"[{q.topic}] {q.question}")
        for f in q.follow_ups:
            print("   -", f)

    # Confirm parsing happened exactly once (single shared ParsedResume object)
    assert pipeline.parsed_resume is parsed
    print("\nOK: single parse reused across ATS + Interview flows")


if __name__ == "__main__":
    main()
