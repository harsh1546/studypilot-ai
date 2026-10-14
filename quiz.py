"""Source-grounded quiz generation with validation to avoid fabricated answer keys."""
import hashlib, json, random, re
from . import llm

SYSTEM = """You are an exacting assessment writer. Use ONLY the provided source excerpt.
Write one unambiguous question testing a meaningful concept, definition, process, cause,
comparison or relationship. Never invent facts. Return exactly one JSON object. For MCQ,
provide four distinct options with exactly one correct answer; distractors must be plausible
but clearly incorrect from the excerpt. The answer and explanation must be directly supported."""

def _sentences(text):
    chunks = re.split(r"(?<=[.!?])\\s+|\\s*[•●▪]\\s*|\\n+", text)
    out = []
    for chunk in chunks:
        chunk = re.sub(r"^\\s*(?:[-*]|\\d+[.)])\\s*", "", chunk).strip()
        if len(chunk) >= 45 and len(re.findall(r"\\w+", chunk)) >= 7:
            out.append(chunk)
    return list(dict.fromkeys(out))

def _source(unit):
    return {"source": unit.source, "loc": unit.loc, "kind": unit.kind, "anchor": unit.anchor}

def _id(unit, question):
    return hashlib.sha256((unit.source + unit.loc + question.casefold()).encode()).hexdigest()[:12]

def _grounded(answer, sent):
    words = [w.casefold() for w in re.findall(r"[A-Za-z0-9-]+", answer) if len(w) > 3]
    if not words: return False
    source = sent.casefold()
    return sum(w in source for w in words) / len(words) >= 0.8

def _fallback(units, asked, kind):
    candidates = [(u, sent) for u in units for sent in _sentences(u.text)]
    random.shuffle(candidates)
    for unit, sent in candidates:
        if kind == "true_false":
            question = f"According to the source, is this statement accurate? {sent}"
            qid = _id(unit, question)
            if qid in asked: continue
            return {"id": qid, "topic": unit.topic, "kind": kind, "answer": "True",
                    "difficulty": "easy", "question": question, "options": ["True", "False"],
                    "explanation": f"The statement is reproduced from {unit.source}, {unit.loc}.",
                    "source": _source(unit)}
        # Do not fabricate distractors from arbitrary words. Ask a source-grounded short
        # answer if no configured language-model key is available.
        if kind == "mcq": continue
        question = f"According to the material, what is stated here? {sent}"
        qid = _id(unit, question)
        if qid in asked: continue
        return {"id": qid, "topic": unit.topic, "kind": "short", "answer": sent,
                "difficulty": "medium", "question": question,
                "explanation": f"This answer is stated in the cited source: {sent}",
                "source": _source(unit)}
    return None

def build(units: list, topic_units: list, asked: set, kind: str = "mcq"):
    if kind not in {"mcq", "short", "true_false"}: kind = "mcq"
    candidates = [(u, sent) for u in units for sent in _sentences(u.text)]
    random.shuffle(candidates)
    if llm.available() and kind != "true_false":
        for unit, sent in candidates[:24]:
            mode = "four-option multiple-choice" if kind == "mcq" else "short-answer"
            prompt = f"""Create one {mode} question from the excerpt below.
Return JSON keys: question, answer, explanation, difficulty, options.
For MCQ, options must be exactly 4 distinct strings and include the answer exactly once.
The answer must be directly supported by the excerpt. Keep the question specific.
EXCERPT: {sent}"""
            try:
                raw = llm.ask(SYSTEM, prompt, max_tokens=500)
                match = re.search(r"\\{.*\\}", raw, re.S) if raw else None
                if not match: continue
                data = json.loads(match.group(0))
                question, answer = str(data.get("question", "")).strip(), str(data.get("answer", "")).strip()
                if len(question) < 12 or len(answer) < 2 or not _grounded(answer, sent): continue
                opts = None
                if kind == "mcq":
                    raw_opts = data.get("options")
                    if not isinstance(raw_opts, list) or len(raw_opts) != 4: continue
                    opts = [str(x).strip() for x in raw_opts]
                    if len({x.casefold() for x in opts}) != 4: continue
                    if sum(x.casefold() == answer.casefold() for x in opts) != 1: continue
                    if any(not x or len(x) > 180 for x in opts): continue
                qid = _id(unit, question)
                if qid in asked: continue
                q = {"id": qid, "topic": unit.topic, "kind": kind, "answer": answer,
                     "question": question, "difficulty": data.get("difficulty", "medium"),
                     "explanation": str(data.get("explanation") or f"The source supports this answer: {sent}"),
                     "source": _source(unit)}
                if opts: q["options"] = opts
                return q
            except Exception:
                continue
    return _fallback(units, asked, kind)

def grade(question: dict, response: str) -> bool:
    expected = re.sub(r"\\s+", " ", question["answer"]).strip().casefold()
    given = re.sub(r"\\s+", " ", response).strip().casefold()
    if given == expected: return True
    normalize = lambda s: re.sub(r"[^a-z0-9 ]", "", s).replace(" the ", " ").replace(" a ", " ").strip()
    return bool(given and normalize(given) == normalize(expected))
