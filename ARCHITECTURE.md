# Architecture

**Ingestion.** `ingest.py` reads PDFs (per page), PPTX (per slide, including notes, tables and picture names) and VTT/SRT transcripts (45-second chunks). Each unit stores file, kind, location and an anchor used to open the exact spot.

**Topics and prerequisites.** `retrieval.py` clusters TF-IDF vectors with k-means, labels each cluster by its top terms, and orders topics by where they first appear. A topic's prerequisite is the topic before it.

**Grounding.** Questions retrieve the top excerpts by cosine similarity. If the best score is below `MIN_SCORE`, the tutor flags the question as not covered instead of answering. Otherwise the LLM is told to answer only from numbered excerpts and cite them.

**Assessment.** `quiz.py` builds a question from one source sentence. Verification checks the answer appears in that sentence. Question hashes prevent repeats. The quiz favours the learner's weakest topics.

**Learner model.** `learner.py` runs Bayesian Knowledge Tracing per topic (init 0.30, learn 0.15, slip 0.10, guess 0.20). A new student starts at the prior; the first quizzes act as the diagnostic.

**Evaluation.** `eval/run_eval.py` reports context recall and precision, off-material refusal, and simulated-student mastery gain and repetition rate. Run RAGAS or DeepEval on the same test set for faithfulness and answer relevancy.
