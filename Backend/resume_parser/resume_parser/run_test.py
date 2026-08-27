from resume_parser import ResumePipeline

pipeline = ResumePipeline()
pipeline.load(pdf_path="Mukul_resume_drivewise.pdf")

ats_result = pipeline.run_ats(job_description="paste JD text here")
print(ats_result.score_result.score)

interview_result = pipeline.run_interview()
for q in interview_result.question_set.questions:
    print(q.question)