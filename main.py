"""StudyPilot API. Run: uvicorn app.main:app --reload (from backend/)"""
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import quiz, tutor
from .diagnosis import prerequisite_chain, root_cause
from .config import FRONTEND_DIR, UPLOAD_DIR
from .ingest import ingest
from .learner import Learner
from .retrieval import KnowledgeBase

app = FastAPI(title="StudyPilot")
kb, learner, asked, live = KnowledgeBase(), Learner(), set(), {}
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Ask(BaseModel):
    question: str
    topic: int | None = None
    lang: str = "en"


class QuizReq(BaseModel):
    topic: int | None = None
    kind: str = "mcq"


class Answer(BaseModel):
    question_id: str
    response: str


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    added = 0
    for f in files:
        dest = UPLOAD_DIR / f.filename
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        try:
            units = ingest(dest)
        except ValueError as e:
            raise HTTPException(400, str(e))
        kb.add(units)
        added += len(units)
    return {"units": added, "topics": kb.topics}


@app.get("/api/topics")
def topics():
    return [{**t, "mastery": round(learner.mastery.get(t["id"], 0.3), 2)} for t in kb.topics]


@app.post("/api/ask")
def ask(req: Ask):
    hits, covered = kb.search(req.question, req.topic)
    return tutor.answer(req.question, hits, covered, req.lang)


@app.post("/api/quiz")
def new_quiz(req: QuizReq):
    if not kb.units:
        raise HTTPException(400, "Upload material first.")
    scope = [u for u in kb.units if req.topic is None or u.topic == req.topic]
    if req.topic is None and not learner.is_new():   # adaptive: favour weak topics
        weak = learner.weakest([t["id"] for t in kb.topics])
        scope = [u for u in kb.units if u.topic in weak] or scope
    q = quiz.build(list(scope), scope, asked, req.kind)
    if q is None:
        raise HTTPException(404, "No new questions left for this scope.")
    asked.add(q["id"])
    live[q["id"]] = q
    return {k: v for k, v in q.items() if k != "answer"}


@app.post("/api/answer")
def check(req: Answer):
    q = live.get(req.question_id)
    if q is None:
        raise HTTPException(404, "Unknown question.")
    ok = quiz.grade(q, req.response)
    learner.update(q["topic"], ok, note=f"Answered '{req.response}' instead of '{q['answer']}'")
    result = {"correct": ok, "answer": q["answer"], "source": q["source"],
              "mastery": round(learner.mastery[q["topic"]], 2), "remedial": None}
    root = None if ok else root_cause(q["topic"], kb.topics, learner.mastery)
    if root is not None:   # teach the missing prerequisite first, with cited excerpts
        name = next(t["name"] for t in kb.topics if t["id"] == root)
        hits, covered = kb.search(name, topic=root)
        result["remedial"] = {"topic": name, "path": [root, q["topic"]], **tutor.answer(name, hits, covered)}
    return result


@app.get("/api/graph")
def graph():
    return {"nodes": [{**t, "mastery": round(learner.mastery.get(t["id"], 0.3), 2)} for t in kb.topics],
            "edges": [{"from": p, "to": t["id"]} for t in kb.topics for p in t["prerequisites"]]}


@app.get("/api/report")
def report():
    names = {t["id"]: t["name"] for t in kb.topics}
    return {"weak": [{"topic": names[t], "mastery": round(learner.mastery.get(t, 0.3), 2)}
                     for t in learner.weakest(list(names))],
            "mistakes": [{"topic": names[w["topic"]], "note": w["note"]} for w in learner.wrong[-5:]],
            "new_student": learner.is_new()}


@app.get("/files/{name}")
def open_source(name: str):
    path = UPLOAD_DIR / name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
