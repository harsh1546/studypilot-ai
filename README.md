# StudyPilot

A source-grounded study companion: upload slides, textbooks and lecture transcripts, then get cited answers, adaptive quizzes and a per-topic mastery model.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # optional; without it the tutor quotes excerpts
cd backend && uvicorn app.main:app --reload
```
Open http://localhost:8000.

## Layout
```
backend/app/   ingest, retrieval, tutor, quiz, learner (BKT), llm, API
backend/eval/  test set and evaluation runner
frontend/      index.html, css/ (base, layout, components), js/ (api, app)
docs/          architecture and approach
```


## Quiz quality and API key setup

The app does **not** contain a hard-coded API key. The optional question-writing provider is Anthropic Claude, configured through `ANTHROPIC_API_KEY`; the model defaults to `claude-sonnet-4-6` and can be overridden with `STUDYPILOT_MODEL`. If no key is set, the app uses source-based fallback questions and does not call an external model. Do not commit real keys to source control.

For scanned PDFs, OCR is best-effort and requires optional system support: PyMuPDF (`pymupdf`), Pillow, pytesseract, and the Tesseract OCR executable. Text PDFs and PPTX extraction work without OCR. The quiz generator now rejects weakly grounded model answers and avoids inventing MCQ distractors when no model is configured.
