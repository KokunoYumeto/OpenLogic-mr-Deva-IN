"""Synchronize generated review input surfaces from durable translation state."""
from pathlib import Path
import shutil

state = Path(r"C:\interlanguage-task-state\openlogic-mr-Deva-IN")
repo = Path(r"C:\interlanguage-production\openlogic-mr-Deva-IN\repo")
(repo / "provenance").mkdir(parents=True, exist_ok=True)
shutil.copyfile(state / "SEGMENT_CANON_USE.jsonl", repo / "provenance" / "SEGMENT_CANON_USE.jsonl")
print((repo / "provenance" / "SEGMENT_CANON_USE.jsonl").stat().st_size)
