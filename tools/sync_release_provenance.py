"""Synchronize sanitized release-scoped provenance from the durable owner state."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "provenance"
FILES = [
    "SOURCE_MANIFEST.jsonl",
    "SEGMENT_CANON_USE.jsonl",
    "CANON_SOURCES.jsonl",
    "CANON_PASSAGES.jsonl",
    "TERM_DECISIONS.jsonl",
]
PRIVATE_KEYS = {"local_path", "page_image", "observation_file", "ocr_path"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scrub(value):
    if isinstance(value, dict):
        return {
            key: scrub(item)
            for key, item in value.items()
            if key not in PRIVATE_KEYS
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str) and re.match(r"^[A-Za-z]:[\\/]", value):
        return "[local research path omitted]"
    return value


def load_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows) -> bytes:
    data = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    path.write_bytes(data)
    return data


parser = argparse.ArgumentParser()
parser.add_argument("--state-dir", required=True, type=Path)
args = parser.parse_args()
state = args.state_dir.resolve()

outputs = {}
for name in FILES:
    source = state / name
    assert source.is_file(), source
    rows = [scrub(row) for row in load_jsonl(source)]
    data = write_jsonl(PROVENANCE / name, rows)
    text = data.decode("utf-8")
    assert not re.search(r'(^|["\s])[A-Za-z]:(?:\\|/)', text), name
    assert not re.search(r"Users[\\/]", text, re.I), name
    assert not re.search(
        r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+", text
    ), name
    outputs[name] = {"records": len(rows), "bytes": len(data), "sha256": sha(data)}

manifest = load_jsonl(PROVENANCE / "SOURCE_MANIFEST.jsonl")
segments = load_jsonl(PROVENANCE / "SEGMENT_CANON_USE.jsonl")
sources = load_jsonl(PROVENANCE / "CANON_SOURCES.jsonl")
passages = load_jsonl(PROVENANCE / "CANON_PASSAGES.jsonl")
terms = load_jsonl(PROVENANCE / "TERM_DECISIONS.jsonl")
translated_units = sorted({row["unit_id"] for row in segments})
assert len(manifest) == 722
assert translated_units == [
    f"OLP-{number:04d}"
    for number in range(4, int(translated_units[-1].split("-")[1]) + 1)
]

receipt = {
    "schema": "openlogic-release-provenance-sync/1",
    "scope": {
        "source_manifest_units": len(manifest),
        "translated_units": len(translated_units),
        "first_translated_unit": translated_units[0],
        "last_translated_unit": translated_units[-1],
        "aligned_segments": len(segments),
        "canon_sources": len(sources),
        "canon_passages": len(passages),
        "term_decisions": len(terms),
    },
    "outputs": outputs,
    "sanitization": {
        "private_path_keys_removed": sorted(PRIVATE_KEYS),
        "absolute_windows_paths": 0,
        "credential_patterns": 0,
    },
    "status": "synchronized",
}
receipt_path = PROVENANCE / "PROVENANCE_SYNC.json"
receipt_path.write_bytes(
    (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
