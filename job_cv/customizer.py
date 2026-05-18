import os
from pathlib import Path

import anthropic

BASE_CV_PATH = Path(__file__).parent.parent / "data" / "cv_base.md"
MODEL = "claude-opus-4-7"


def load_base_cv() -> str:
    if not BASE_CV_PATH.exists():
        raise FileNotFoundError(
            f"Base CV not found at {BASE_CV_PATH}\n"
            "Create it with your resume content in Markdown format."
        )
    text = BASE_CV_PATH.read_text().strip()
    if not text:
        raise ValueError(f"{BASE_CV_PATH} is empty. Add your resume content first.")
    return text


def customize_cv(base_cv: str, job_desc: str, company: str, role: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""You are an expert CV writer. Customize the CV below for this specific job application.

## Target Job
Company: {company}
Role: {role}

## Job Description
{job_desc}

## Base CV
{base_cv}

## Instructions
- Rewrite the professional summary to speak directly to this role and company
- Reorder experience bullet points so the most relevant ones appear first
- Highlight skills and achievements that match the job requirements
- Weave in keywords from the job description naturally
- Keep all facts accurate — do not invent anything
- Preserve the same Markdown structure and headings
- Output ONLY the customized CV in Markdown, nothing else""",
            }
        ],
    )
    return response.content[0].text.strip()


def generate_cover_letter(base_cv: str, job_desc: str, company: str, role: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": f"""Write a compelling, personalized cover letter for this job application.

## Target Job
Company: {company}
Role: {role}

## Job Description
{job_desc}

## My Background
{base_cv}

## Instructions
- Open with a strong hook that references the specific role and company
- Paragraph 2: match my most relevant experience to the key job requirements
- Paragraph 3: show genuine interest in the company's work or mission
- Close with a clear call to action
- Keep it to 3-4 short paragraphs, professional tone
- Output ONLY the cover letter in Markdown, nothing else""",
            }
        ],
    )
    return response.content[0].text.strip()
