# CV Analyzer

AI-powered career assistant built with Streamlit. Compare your profile with a
job description, build a tailored CV, search real vacancies, train for
behavioral interviews with a STAR coach, and track your applications — in
**Portuguese, English, and Spanish**.

> Free project — no payments, no accounts. Your API keys are used only during
> the session and are never written to disk.

## Features

### CV Analyzer
- **Multi-provider support** — OpenCode Zen (free), Google Gemini, OpenAI, Anthropic (Claude), GitHub Copilot
- **Provider auto-detection** — paste any API key in the sidebar and the provider/model are selected automatically
- **Session-only API keys** — paste your key in the sidebar; never saved to disk
- Profile via PDF upload or pasted text (LinkedIn / resume)
- Structured results: compatibility score, strengths, gaps (with per-category progress), improvement suggestions
- **Tailored CV** — rewrite your CV for a specific job description
- **Cover letter** and **follow-up email** generators based on the analysis

### CV Builder
- Paste LinkedIn text or upload a PDF profile
- AI extracts structured data (name, experience, education, skills, etc.)
- Two layouts:
  - **Advanced** — two-column with colored sidebar, optional profile photo
  - **Simple** — clean single-column with section dividers
- Live HTML preview
- Export as **DOCX, PDF** (ATS-safe) or **HTML**

### Job Search
- Real job listings via the free Adzuna API (app_id / app_key in the sidebar)
- Filter by keywords, location, and country
- Send any posting straight to the Analyzer for a compatibility check

### STAR Coach
- Generates 5 behavioral interview questions from a job description
- Grade your answers with the **S.T.A.R. method** (Situation, Task, Action, Result)
- Detailed per-component feedback, overall score, and an improved answer suggestion
- Smart fallback questions when the model is unavailable (localized)

### Application Tracker
- Local **SQLite** tracker (`src/tracker.db`) — register companies, roles, CV version used, job URL, notes, status
- Filter by CV version, update/delete entries, statistics, follow-up date
- Fully included in the LGPD "clear my data" flow

### Privacy (LGPD)
- Consent gate on first use — the app is blocked until you accept
- `no-save` mode prevents profile persistence
- One-click **erase all data** (profiles, tracker, session state)

## Supported providers & keys

| Provider | Env var | Sidebar needed? |
|---|---|---|
| OpenCode Zen | `OPENCODE_ZEN_API_KEY` | No (free default) |
| Google Gemini | `GEMINI_API_KEY` | Yes |
| OpenAI | `OPENAI_API_KEY` | Yes |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | Yes |
| GitHub Copilot | `COPILOT_API_KEY` | Yes |

Job Search uses Adzuna (sidebar `app_id`/`app_key`).

## Project structure

```
cv-analyzer/
├── .env.example
├── .github/workflows/ci.yml      # automated tests on every push/PR
├── requirements.txt
├── README.md
├── src/
│   ├── app.py               # entry point — 5 tabs (Analyzer | Builder | Job Search | Tracker | STAR)
│   ├── config.py            # paths, constants, AI prompts
│   ├── i18n.py              # translations (pt / en / es)
│   ├── providers.py         # provider registry, API keys, analysis engine
│   ├── ui.py                # Analyzer UI components, inputs, LGPD
│   ├── cv_builder.py        # Builder page logic + export buttons
│   ├── cv_export.py         # DOCX / PDF export
│   ├── cv_templates.py      # HTML/CSS CV templates (Advanced & Simple)
│   ├── cv_utils.py          # shared JSON parsing / CV structuring helpers
│   ├── star_coach.py        # STAR questions + grading engine
│   ├── star_ui.py           # STAR Coach UI
│   ├── tracker_manager.py   # SQLite persistence layer
│   ├── tracker_ui.py        # Application Tracker UI
│   ├── job_search.py        # Adzuna job search client
│   ├── job_fetcher.py       # job description fetcher
│   ├── pdf_extractor.py     # PDF text extraction
│   ├── profile_manager.py   # local JSON profile persistence
│   └── progress_utils.py    # AI-call progress animation
└── tests/                   # automated test suite (pytest)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest (for tests only)
```

### 2. (Optional) Default API keys

Copy `.env.example` to `.env` and fill in keys you want pre-loaded:

```bash
cp .env.example .env
```

Or paste keys directly in the sidebar at runtime.

### 3. Run the app

```bash
streamlit run src/app.py
```

Opens at `http://localhost:8501`.

## How to use

### Analyzer tab
1. Choose a provider in the sidebar (free models need no key) or paste an API key to auto-detect
2. Paste the candidate profile and a job description
3. Click **Analyze Compatibility**
4. Optional: **Generate Tailored CV**, **Cover Letter**, **Follow-up Email**

### Builder tab
1. Choose a layout (Advanced or Simple) and accent color
2. Paste LinkedIn text or upload a PDF (optional photo for Advanced)
3. Click **Generate CV**
4. Preview and download as **DOCX, PDF** or **HTML**

### Job Search tab
1. Enter your Adzuna `app_id`/`app_key` in the sidebar
2. Search by keyword, location, and country
3. Click **Analyze Compatibility** on any posting

### Tracker tab
Register applications with company, role, CV version used, job URL, notes and
status; filter, update, delete, and view statistics.

### STAR tab
1. Paste a job description (or use the one from the Analyzer)
2. Click **Start Training** to get 5 questions
3. Answer each one and get S.T.A.R. feedback + score

## Running the tests

```bash
python -m pytest -q
```

Covers: i18n parity across pt/en/es, PDF/DOCX export (with non-ASCII input),
STAR scoring robustness, shared CV helpers, tracker CRUD, provider detection.

## Deploy

### Streamlit Community Cloud
1. Push this repo to GitHub
2. In Streamlit Community Cloud create a new app pointing to `src/app.py`
3. Add secrets in the dashboard (same keys as `.env.example`) if you want defaults

### Docker
```bash
docker compose up -d --build          # build + start with persistence
docker build -t cv-analyzer .
docker run -p 8501:8501 cv-analyzer
```

Full operational details (env vars, healthcheck, persistence, proxy, release
and rollback) are in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Adding a new provider

Edit `src/providers.py`:
1. Add an entry to `PROVIDERS` with `name`, `base_url`, `env_key`, `json_mode`, `needs_key`
2. Add model entries to `MODELS`
3. If the API is non-OpenAI (like Anthropic), add a branch in `analyze_profile()`

## License

MIT — see [LICENSE](LICENSE).