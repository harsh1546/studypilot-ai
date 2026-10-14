"""Source-grounded answers: cite excerpts, flag anything the material does not cover."""
from . import llm

SYSTEM = (
    "You are a study tutor. Answer ONLY from the numbered excerpts and cite them like [1]. "
    "If the excerpts do not answer the question, say so. Keep it short and clear."
)


HINDI = " Reply in Hindi (Devanagari) and keep technical terms in English."


def answer(question: str, hits: list, covered: bool, lang: str = "en") -> dict:
    cites = [{"n": i + 1, "source": u.source, "loc": u.loc, "kind": u.kind,
              "anchor": u.anchor, "text": u.text[:280], "score": round(s, 2)}
             for i, (u, s) in enumerate(hits)]
    if not covered:
        return {"covered": False, "citations": [],
                "answer": "Your uploaded material doesn't cover this. Anything I add would come from "
                          "outside your course, so treat it as unverified."}
    context = "\n".join(f"[{c['n']}] ({c['source']}, {c['loc']}) {c['text']}" for c in cites)
    text = llm.ask(SYSTEM + (HINDI if lang == "hi" else ""), f"Excerpts:\n{context}\n\nQuestion: {question}")
    if text is None:  # offline mode: show the best excerpt instead of generating prose
        text = f"From your material: {cites[0]['text']} [1]"
    return {"covered": True, "answer": text, "citations": cites}
