# resume_parser

Reusable PDF resume parser that extracts complete structured data **once**,
then feeds two independent output flows (ATS scoring, Interview questions)
from that single parse — matching this flow:

```
Resume PDF
    │
    ▼
CommonParser (PyMuPDF + spaCy + regex + section detection)
    │
    ▼
ParsedResume (complete structured data, extracted ONCE)
    │
    ├──► ATSOutputBuilder ──(+ Job Description)──► ATSScorer ──► score, matched/missing skills, suggestions
    │
    └──► InterviewOutputBuilder ──► InterviewQuestionGenerator ──► questions + follow-ups
```

## Module layout

```
resume_parser/
  models.py                  # Shared dataclasses: ParsedResume, ContactInfo, Education,
                              # Experience, Project, Certification, Skill.
                              # The ONLY contract between parsing and everything downstream.

  parser/                    # Parsing concern — never imports ats/ or interview/
    section_detector.py      # Splits raw text into SUMMARY/SKILLS/EDUCATION/... blocks
    extractors.py            # Regex + spaCy field extraction per section
    common_parser.py         # CommonResumeParser: PDF bytes -> ParsedResume (parse ONCE)

  outputs/                   # Pure transformation of ParsedResume -> flavored data.
                              # No scoring, no question generation here.
    ats_output.py             # ATSOutputBuilder -> ATSResumeData (flat, keyword-oriented)
    interview_output.py       # InterviewOutputBuilder -> InterviewResumeData (topic-oriented)

  ats/                       # ATS-specific logic. Only module that knows about a Job Description.
    ats_scorer.py             # ATSScorer: ATSResumeData + JD -> score, matched/missing, suggestions

  interview/                 # Interview-specific logic. Only module that generates questions.
    question_generator.py     # InterviewQuestionGenerator: InterviewResumeData -> questions + follow-ups

  pipeline.py                 # ResumePipeline facade — the front door. Guarantees the resume
                               # is parsed exactly once and shared by both flows.
```

## Why this shape

- **Single parse, two consumers.** `CommonResumeParser` is the only place PDF
  bytes are touched. `ResumePipeline.load()` caches the resulting
  `ParsedResume`; `run_ats()` and `run_interview()` both read from that same
  cached object, so parsing logic is never duplicated between the ATS and
  Interview paths.
- **Section detection is separate from field extraction.** `section_detector.py`
  only answers "where does EDUCATION start/end"; `extractors.py` only answers
  "given this block of text, what's the degree/GPA/dates". Each is testable
  independently and either can be swapped (e.g. section detection upgraded to
  a layout-aware model) without touching the other.
- **Output builders never score or generate questions.** `ats_output.py` and
  `interview_output.py` only reshape `ParsedResume` into the structure each
  downstream engine wants. All job-description-aware logic lives in
  `ats_scorer.py`; all question-generation logic lives in
  `question_generator.py`. This is what lets you swap the scorer or the
  question generator (e.g. for an LLM-backed version) without touching the
  parser or the other flow at all.
- **`ResumePipeline` is the only place that wires it all together.** Every
  submodule is independently importable/testable, but application code
  (Django views, Celery tasks, etc.) should only need `ResumePipeline`.

## Usage

```python
from resume_parser import ResumePipeline

pipeline = ResumePipeline()
pipeline.load(pdf_path="resume.pdf")        # parses ONCE — cached
# or: pipeline.load(pdf_bytes=uploaded_file.read())

# User selects ATS
ats_result = pipeline.run_ats(job_description=jd_text)
print(ats_result.score_result.score)
print(ats_result.score_result.matched_skills)
print(ats_result.score_result.missing_skills)
print(ats_result.score_result.suggestions)

# User selects Interview (same parsed resume, no re-parsing)
interview_result = pipeline.run_interview()
for q in interview_result.question_set.questions:
    print(q.topic, "-", q.question)
    print("  follow-ups:", q.follow_ups)

# Adaptive follow-up after a candidate answers a question live:
more_followups = pipeline._interview_generator.generate_followups(
    interview_result.question_set.questions[0],
    candidate_answer="I used it for a class project.",
)
```

## Install

```bash
pip install pymupdf spacy
python -m spacy download en_core_web_sm
```

spaCy is used only to improve name detection (PERSON NER) in the contact
block; if the model isn't installed, `CommonResumeParser` falls back to a
regex-only heuristic automatically (`load_spacy=True` by default, or pass
`load_spacy=False` to skip spaCy entirely).

## Extending

- **Swap in an LLM for JD skill extraction / question generation:** both
  `ATSScorer._extract_candidate_skills()` and
  `InterviewQuestionGenerator._skill_questions()` (etc.) are isolated enough
  to replace with a call into an LLM service without touching the parser or
  the other output flow — this maps directly onto Jobrix's AI/ML Services
  Layer (LLM service via OpenAI/Gemini).
- **Add a new output flow** (e.g. "Resume Summary Generator"): add
  `outputs/summary_output.py`, consume `ParsedResume`, wire a new
  `run_summary()` method onto `ResumePipeline`. Zero changes needed to
  `parser/`, `ats/`, or `interview/`.
