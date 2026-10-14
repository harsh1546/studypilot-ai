"""Turn PDFs, slide decks and lecture transcripts into cited content units.

Every unit keeps its origin: page, slide number or video timestamp.
"""
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from pypdf import PdfReader
from pptx import Presentation


@dataclass
class Unit:
    id: str
    source: str      # file name
    kind: str        # pdf | slide | video
    loc: str         # "p. 4", "slide 7", "12:30"
    anchor: str      # value used to open the exact spot (page, slide, seconds)
    text: str
    topic: int = -1

    def dict(self):
        return asdict(self)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _pdf(path: Path):
    for n, page in enumerate(PdfReader(str(path)).pages, 1):
        yield "pdf", f"p. {n}", str(n), page.extract_text() or ""


def _pptx(path: Path):
    for n, slide in enumerate(Presentation(str(path)).slides, 1):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.shape_type == 13:  # picture: keep alt text so figures stay searchable
                parts.append(f"[figure: {shape.name}]")
            if getattr(shape, "has_table", False) and shape.has_table:
                parts += [c.text for r in shape.table.rows for c in r.cells]
        if slide.has_notes_slide:
            parts.append(slide.notes_slide.notes_text_frame.text)
        yield "slide", f"slide {n}", str(n), " ".join(parts)


_TS = re.compile(r"(?:(\d+):)?(\d+):(\d+)[.,]\d+\s*-->")


def _transcript(path: Path):
    """Group .vtt/.srt cues into ~45 second chunks with their start time."""
    chunk, start = [], None
    for line in path.read_text(errors="ignore").splitlines():
        m = _TS.search(line)
        if m:
            h, mnt, s = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
            sec = h * 3600 + mnt * 60 + s
            if start is None:
                start = sec
            elif sec - start > 45 and chunk:
                yield "video", f"{start // 60}:{start % 60:02d}", str(start), " ".join(chunk)
                chunk, start = [], sec
        elif line.strip() and not line.strip().isdigit() and "WEBVTT" not in line:
            chunk.append(line.strip())
    if chunk:
        yield "video", f"{(start or 0) // 60}:{(start or 0) % 60:02d}", str(start or 0), " ".join(chunk)


READERS = {".pdf": _pdf, ".pptx": _pptx, ".vtt": _transcript, ".srt": _transcript}


def ingest(path: Path) -> list[Unit]:
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    units = []
    for kind, loc, anchor, text in reader(path):
        text = _clean(text)
        if len(text) > 40:
            units.append(Unit(f"{path.stem}-{len(units)}", path.name, kind, loc, anchor, text))
    return units
