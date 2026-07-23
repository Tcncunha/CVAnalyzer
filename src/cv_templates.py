"""
HTML/CSS templates for CV rendering.

Two layouts:
  - ADVANCED: two-column with colored sidebar (photo, contact, skills)
  - SIMPLE:   clean single-column with section dividers
"""

from html import escape


def _e(text: str) -> str:
    """Escape HTML special characters."""
    return escape(text or "")


def _join(items: list[str], sep: str = ", ") -> str:
    """Join non-empty items with a separator."""
    return _e(sep.join(i for i in items if i.strip()))


# =============================================================================
# ADVANCED TEMPLATE -- two-column, sidebar with photo
# =============================================================================

def render_advanced(cv: dict, photo_html: str = "") -> str:
    """Return a full HTML document for the Advanced CV layout.

    cv keys: name, title, email, phone, location, linkedin, summary,
             skills, experience (list of dicts), education (list of dicts),
             languages, certifications
    """
    name = _e(cv.get("name", ""))
    title = _e(cv.get("title", ""))
    email = _e(cv.get("email", ""))
    phone = _e(cv.get("phone", ""))
    location = _e(cv.get("location", ""))
    linkedin = _e(cv.get("linkedin", ""))
    summary = _e(cv.get("summary", ""))
    skills = cv.get("skills", [])
    experience = cv.get("experience", [])
    education = cv.get("education", [])
    languages = cv.get("languages", [])
    certifications = cv.get("certifications", [])

    # Build experience HTML
    exp_html = ""
    for job in experience:
        exp_html += f"""
        <div class="exp-item">
            <div class="exp-header">
                <span class="exp-role">{_e(job.get('role', ''))}</span>
                <span class="exp-dates">{_e(job.get('dates', ''))}</span>
            </div>
            <div class="exp-company">{_e(job.get('company', ''))}</div>
            <div class="exp-desc">{_e(job.get('description', ''))}</div>
        </div>"""

    # Build education HTML
    edu_html = ""
    for edu in education:
        edu_html += f"""
        <div class="edu-item">
            <div class="edu-degree">{_e(edu.get('degree', ''))}</div>
            <div class="edu-school">{_e(edu.get('school', ''))} -- {_e(edu.get('dates', ''))}</div>
        </div>"""

    # Build skills HTML
    skills_html = "".join(f'<span class="skill-tag">{_e(s)}</span>' for s in skills if s.strip())

    # Build languages HTML
    lang_html = "".join(f'<li>{_e(l)}</li>' for l in languages if l.strip())

    # Build certifications HTML
    cert_html = "".join(f'<li>{_e(c)}</li>' for c in certifications if c.strip())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f0f0; }}
  .page {{
      width: 210mm; min-height: 297mm; margin: 0 auto;
      display: flex; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  }}
  /* --- Sidebar --- */
  .sidebar {{
      width: 35%; background: #1a2740; color: #e0e0e0; padding: 30px 20px;
      display: flex; flex-direction: column; gap: 18px;
  }}
  .sidebar h1 {{ color: #fff; font-size: 22px; margin-bottom: 2px; }}
  .sidebar .title {{ color: #7eb8da; font-size: 13px; margin-bottom: 8px; }}
  .sidebar .photo {{ text-align: center; margin-bottom: 10px; }}
  .sidebar .photo img {{
      width: 110px; height: 110px; border-radius: 50%; object-fit: cover;
      border: 3px solid #7eb8da;
  }}
  .sidebar .section-title {{
      color: #7eb8da; font-size: 11px; text-transform: uppercase;
      letter-spacing: 1.5px; border-bottom: 1px solid #3a5068;
      padding-bottom: 4px; margin-bottom: 6px;
  }}
  .contact-item {{ font-size: 12px; margin-bottom: 4px; word-break: break-all; }}
  .skill-tag {{
      display: inline-block; background: #2a3f56; color: #c5d8e8;
      padding: 3px 8px; border-radius: 3px; font-size: 11px; margin: 2px;
  }}
  .sidebar ul {{ list-style: none; padding: 0; font-size: 12px; }}
  .sidebar li {{ margin-bottom: 3px; }}

  /* --- Main content --- */
  .main {{
      width: 65%; padding: 30px 28px; display: flex; flex-direction: column; gap: 16px;
  }}
  .main .section-title {{
      font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px;
      color: #1a2740; border-bottom: 2px solid #1a2740;
      padding-bottom: 4px; margin-bottom: 8px; font-weight: 700;
  }}
  .summary {{ font-size: 12.5px; line-height: 1.55; color: #333; }}
  .exp-item {{ margin-bottom: 12px; }}
  .exp-header {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .exp-role {{ font-weight: 600; font-size: 13px; color: #1a2740; }}
  .exp-dates {{ font-size: 11px; color: #777; }}
  .exp-company {{ font-size: 12px; color: #555; font-style: italic; margin-bottom: 3px; }}
  .exp-desc {{ font-size: 12px; color: #444; line-height: 1.5; }}
  .edu-item {{ margin-bottom: 8px; }}
  .edu-degree {{ font-weight: 600; font-size: 13px; color: #1a2740; }}
  .edu-school {{ font-size: 12px; color: #555; }}
</style>
</head>
<body>
<div class="page">
  <div class="sidebar">
    {photo_html}
    <h1>{name}</h1>
    <div class="title">{title}</div>

    <div>
      <div class="section-title">Contact</div>
      <div class="contact-item">{email}</div>
      <div class="contact-item">{phone}</div>
      <div class="contact-item">{location}</div>
      <div class="contact-item">{linkedin}</div>
    </div>

    <div>
      <div class="section-title">Skills</div>
      {skills_html}
    </div>

    {"<div><div class='section-title'>Languages</div><ul>" + lang_html + "</ul></div>" if lang_html else ""}
    {"<div><div class='section-title'>Certifications</div><ul>" + cert_html + "</ul></div>" if cert_html else ""}
  </div>

  <div class="main">
    <div>
      <div class="section-title">Professional Summary</div>
      <div class="summary">{summary}</div>
    </div>

    <div>
      <div class="section-title">Experience</div>
      {exp_html}
    </div>

    <div>
      <div class="section-title">Education</div>
      {edu_html}
    </div>
  </div>
</div>
</body>
</html>"""


# =============================================================================
# SIMPLE TEMPLATE -- single-column, clean
# =============================================================================

def render_simple(cv: dict) -> str:
    """Return a full HTML document for the Simple CV layout."""
    name = _e(cv.get("name", ""))
    title = _e(cv.get("title", ""))
    email = _e(cv.get("email", ""))
    phone = _e(cv.get("phone", ""))
    location = _e(cv.get("location", ""))
    linkedin = _e(cv.get("linkedin", ""))
    summary = _e(cv.get("summary", ""))
    skills = cv.get("skills", [])
    experience = cv.get("experience", [])
    education = cv.get("education", [])
    languages = cv.get("languages", [])
    certifications = cv.get("certifications", [])

    # Contact line
    contact_parts = [p for p in [email, phone, location, linkedin] if p]
    contact_line = " &nbsp;|&nbsp; ".join(contact_parts)

    # Experience
    exp_html = ""
    for job in experience:
        desc = _e(job.get("description", "")).replace("\n", "<br>")
        exp_html += f"""
        <div class="entry">
            <div class="entry-top">
                <span class="entry-title">{_e(job.get('role', ''))}</span>
                <span class="entry-dates">{_e(job.get('dates', ''))}</span>
            </div>
            <div class="entry-sub">{_e(job.get('company', ''))}</div>
            <div class="entry-desc">{desc}</div>
        </div>"""

    # Education
    edu_html = ""
    for edu in education:
        edu_html += f"""
        <div class="entry">
            <div class="entry-top">
                <span class="entry-title">{_e(edu.get('degree', ''))}</span>
                <span class="entry-dates">{_e(edu.get('dates', ''))}</span>
            </div>
            <div class="entry-sub">{_e(edu.get('school', ''))}</div>
        </div>"""

    # Skills
    skills_str = _join(skills, " &bull; ")

    # Languages
    lang_str = _join(languages, ", ")

    # Certifications
    cert_html = "".join(f"<li>{_e(c)}</li>" for c in certifications if c.strip())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; }}
  .page {{
      width: 210mm; min-height: 297mm; margin: 0 auto;
      background: #fff; padding: 36px 40px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}
  .header {{ text-align: center; margin-bottom: 16px; }}
  .header h1 {{ font-size: 26px; color: #222; margin-bottom: 2px; }}
  .header .subtitle {{ font-size: 14px; color: #666; margin-bottom: 6px; }}
  .header .contact {{ font-size: 12px; color: #555; }}
  .divider {{ border: none; border-top: 2px solid #222; margin: 12px 0; }}
  .divider-thin {{ border: none; border-top: 1px solid #ddd; margin: 8px 0; }}
  .section-title {{
      font-size: 12px; text-transform: uppercase; letter-spacing: 2px;
      color: #222; font-weight: 700; margin-bottom: 8px;
  }}
  .summary {{ font-size: 12.5px; line-height: 1.6; color: #444; margin-bottom: 14px; }}
  .skills {{ font-size: 12.5px; color: #444; margin-bottom: 14px; line-height: 1.6; }}
  .entry {{ margin-bottom: 12px; }}
  .entry-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .entry-title {{ font-weight: 600; font-size: 13px; color: #222; }}
  .entry-dates {{ font-size: 11.5px; color: #888; }}
  .entry-sub {{ font-size: 12px; color: #666; font-style: italic; margin-bottom: 2px; }}
  .entry-desc {{ font-size: 12px; color: #444; line-height: 1.55; }}
  .two-col {{ display: flex; gap: 30px; }}
  .two-col > div {{ flex: 1; }}
  ul {{ font-size: 12px; color: #444; padding-left: 16px; }}
  li {{ margin-bottom: 2px; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{name}</h1>
    <div class="subtitle">{title}</div>
    <div class="contact">{contact_line}</div>
  </div>

  <hr class="divider">

  <div class="section-title">Professional Summary</div>
  <div class="summary">{summary}</div>

  <div class="section-title">Experience</div>
  {exp_html}

  <hr class="divider-thin">

  <div class="section-title">Education</div>
  {edu_html}

  <hr class="divider-thin">

  <div class="two-col">
    <div>
      <div class="section-title">Skills</div>
      <div class="skills">{skills_str}</div>
    </div>
    <div>
      <div class="section-title">Languages</div>
      <div class="skills">{lang_str}</div>
    </div>
  </div>

  {"<hr class='divider-thin'><div class='section-title'>Certifications</div><ul>" + cert_html + "</ul>" if cert_html else ""}
</div>
</body>
</html>"""
