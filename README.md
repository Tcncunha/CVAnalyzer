# CV Analyzer

AI-powered career assistant with two tools: **CV Analyzer** (match your profile against a job) and **CV Builder** (generate a professional CV from your LinkedIn profile).

## Features

### CV Analyzer
- **Multi-provider support** -- OpenCode Zen (free), Google Gemini, OpenAI, Anthropic (Claude)
- **Session-only API keys** -- paste your key in the sidebar; never saved to disk
- PDF upload or text paste for candidate profiles
- PT/EN language toggle
- Structured results: compatibility score, strengths, gaps, improvement suggestions

### CV Builder
- Paste LinkedIn text or upload a PDF profile
- AI extracts structured data (name, experience, education, skills, etc.)
- Two layout options:
  - **Advanced** -- two-column with colored sidebar, optional profile photo
  - **Simple** -- clean single-column with section dividers
- Live HTML preview inside the app
- Download as HTML or raw JSON

## Project Structure

```
CVAnalyzer/
├── .env.example
├── requirements.txt
├── README.md
└── src/
    ├── app.py              # entry point with tabs (Analyzer | Builder)
    ├── config.py           # paths, constants, AI prompt
    ├── i18n.py             # translations (PT/EN)
    ├── providers.py        # provider/model registry, API key handling, analysis engine
    ├── ui.py               # Analyzer UI components
    ├── cv_builder.py       # Builder page logic
    ├── cv_templates.py     # HTML/CSS CV templates (Advanced & Simple)
    ├── pdf_extractor.py    # PDF text extraction
    ├── profile_manager.py  # local JSON profile persistence
    └── profiles_json/      # saved profiles (auto-created)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Set default API keys

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

## How to Use

### Analyzer Tab
1. Select a provider in the sidebar (free models need no key)
2. Paste the candidate profile and a job description
3. Click **Analyze Compatibility**

### Builder Tab
1. Choose a layout (Advanced or Simple)
2. Paste LinkedIn text or upload a PDF
3. (Advanced only) optionally upload a profile photo
4. Click **Generate CV**
5. Preview the result and download as HTML or JSON

## Adding a New Provider

Edit `src/providers.py`:
1. Add an entry to `PROVIDERS` with `name`, `base_url`, `env_key`, `json_mode`, `needs_key`
2. Add model entries to `MODELS`
3. If the API is non-OpenAI (like Anthropic), add a branch in `analyze_profile()`
