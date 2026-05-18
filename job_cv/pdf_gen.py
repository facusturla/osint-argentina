import re
from datetime import datetime
from pathlib import Path

import markdown as md_lib

CV_CSS = """
@page { margin: 2cm 2.2cm; size: A4; }
* { box-sizing: border-box; }
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a1a1a;
}
h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #0d1b2a;
    margin: 0 0 2px 0;
    letter-spacing: -0.5px;
}
h2 {
    font-size: 11pt;
    font-weight: 700;
    color: #0d1b2a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-bottom: 1.5px solid #0d1b2a;
    padding-bottom: 3px;
    margin: 18px 0 8px 0;
}
h3 {
    font-size: 10.5pt;
    font-weight: 600;
    color: #1a1a1a;
    margin: 10px 0 2px 0;
}
p { margin: 4px 0; }
ul { margin: 4px 0 8px 0; padding-left: 16px; }
li { margin-bottom: 2px; }
a { color: #0d1b2a; text-decoration: none; }
em { color: #444; }
strong { font-weight: 600; }
.contact { color: #555; font-size: 9.5pt; margin-bottom: 12px; }
"""

COVER_CSS = """
@page { margin: 3cm 2.5cm; size: A4; }
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1a1a1a;
}
h1, h2 { color: #0d1b2a; }
p { margin: 0 0 14px 0; }
"""


def _to_html(text: str, title: str, css: str) -> str:
    body = md_lib.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>{body}</body>
</html>"""


def _write_pdf(html: str, path: Path) -> bool:
    try:
        from weasyprint import HTML

        HTML(string=html).write_pdf(str(path))
        return True
    except Exception:
        return False


def save_outputs(company: str, role: str, cv_text: str, cover_letter: str | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^\w]+", "_", f"{company}_{role}")[:50].strip("_")
    output_dir = Path(__file__).parent.parent / "applications" / f"{timestamp}_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {}
    job_label = f"{role} — {company}"

    # CV
    cv_md_path = output_dir / "cv.md"
    cv_md_path.write_text(cv_text)
    files["cv_md"] = str(cv_md_path)

    cv_html = _to_html(cv_text, f"CV | {job_label}", CV_CSS)
    cv_html_path = output_dir / "cv.html"
    cv_html_path.write_text(cv_html)
    files["cv_html"] = str(cv_html_path)

    cv_pdf_path = output_dir / "cv.pdf"
    if _write_pdf(cv_html, cv_pdf_path):
        files["cv_pdf"] = str(cv_pdf_path)

    # Cover letter
    if cover_letter:
        cl_md_path = output_dir / "cover_letter.md"
        cl_md_path.write_text(cover_letter)
        files["cover_letter_md"] = str(cl_md_path)

        cl_html = _to_html(cover_letter, f"Cover Letter | {job_label}", COVER_CSS)
        cl_html_path = output_dir / "cover_letter.html"
        cl_html_path.write_text(cl_html)
        files["cover_letter_html"] = str(cl_html_path)

        cl_pdf_path = output_dir / "cover_letter.pdf"
        if _write_pdf(cl_html, cl_pdf_path):
            files["cover_letter_pdf"] = str(cl_pdf_path)

    return files
