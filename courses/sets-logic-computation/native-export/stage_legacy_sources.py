"""Stage the native Marathi SLC tools from a thin course and canonical sources."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

from olpkit.assembly import GitSnapshot
from olpkit.cache import SourceCache, relative_path
from olpkit.shims import apply_shims


FONT_NAMES = ("NotoSerifDevanagari.ttf", "OLMarathiSerif-Regular.ttf",
              "OLMarathiSerif-Bold.ttf", "OFL.txt", "MANIFEST.json")
ROOT_FILES = ("README.md", "LICENSE-SLC.md", "ASSET-CREDITS.md",
              "ASSET-MANIFEST.json", "FONT-CREDITS.md", "slc-config.sty", "slc-envs.sty")
MOUNTS = (
    ("native-drivers", ""),
    ("native-tools", ""),
    ("include", "include"),
    ("illustrations", "illustrations"),
    ("config", "locale/mr/config"),
    ("locale", "locale/mr/locale"),
    ("locale/photocredits", "locale/mr/photocredits"),
    ("fonts", "fonts"),
    ("font-notices", "font-notices"),
    ("assets/tex/nowidow", "vendor/nowidow"),
    ("bib", "open-logic/bib"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_bytes(root, name):
    target = root / relative_path(name)
    if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError(f"Missing or unsafe staging input {name}")
    return target.read_bytes()


def add(inputs, name, data):
    relative_path(name)
    if name in inputs:
        raise ValueError(f"Duplicate staging input {name}")
    inputs[name] = data


def stage_inputs(course, snapshot, cache, lock, dependencies, shims):
    contract = snapshot.read_many(["olp-edition.toml", "units.jsonl"])
    edition = tomllib.loads(contract["olp-edition.toml"].decode("utf8"))
    rows = {}
    for line in lock.read_text(encoding="utf8").splitlines():
        uid, name = line.split("\t")
        path = relative_path(name)
        if len(path.parts) < 2 or path.parts[0] != "content" or path.suffix != ".tex" or name in rows:
            raise ValueError(f"Unexpected import lock row for {name}")
        rows[name] = uid
    if len(rows) != 176 or len(set(rows.values())) != 176:
        raise ValueError("Marathi SLC requires exactly 176 unique unit IDs and paths")
    ledger = {row["path"]: row for row in map(json.loads,
              contract["units.jsonl"].decode("utf8").splitlines())}

    inputs = {}
    for name in ROOT_FILES:
        add(inputs, name, file_bytes(course, name))
    for source, destination in MOUNTS:
        base = course / source
        for item in sorted(base.iterdir()):
            if item.is_dir():
                continue
            add(inputs, str(PurePosixPath(destination) / item.name),
                file_bytes(course, item.relative_to(course).as_posix()))
    target_root = edition["paths"]["content"]
    unit_paths = {name: target_root + "/" + name.removeprefix("content/") for name in rows}
    for name, data in snapshot.read_many(["fonts/" + name for name in FONT_NAMES]).items():
        add(inputs, name, data)
    unit_bytes = snapshot.read_many(unit_paths.values())
    for name, uid in rows.items():
        if ledger[name]["id"] != uid:
            raise ValueError(f"Import lock and canonical ledger disagree at {name}")
        data = unit_bytes[unit_paths[name]]
        if digest(data) != ledger[name]["tr_sha256"]:
            raise ValueError(f"Canonical source hash differs at {name}")
        add(inputs, "locale/mr/" + name, data)

    pins = {key: edition["pins"][key]["commit"] for key in ("olp", "photos", "portraits")}
    cache_dirs = {key: cache.require(key, pin)[0] for key, pin in pins.items()}
    upstream = {}
    provenance = json.loads(dependencies.read_text(encoding="utf8"))
    for name, row in provenance.items():
        data = file_bytes(cache_dirs[row["source"]], row["path"])
        if digest(data) != row["pinned_sha256"]:
            raise ValueError(f"Pinned dependency hash differs at {name}")
        if row["source"] == "olp":
            upstream[row["path"]] = data
        else:
            add(inputs, name, data)
    upstream, _ = apply_shims(upstream, {
        "locale": edition["locale"], "engine": edition["engine"], "script": edition["script"],
    }, directory=shims)
    for name, data in upstream.items():
        add(inputs, "open-logic/" + name, data)
    for name, row in provenance.items():
        if digest(inputs[name]) != row["output_sha256"]:
            raise ValueError(f"Native dependency hash differs at {name}")
    for name, data in inputs.items():
        if name.endswith((".md", ".tex", ".sty", ".json", ".ps1", ".py")):
            if re.search(rb"(?i)(?:interlanguage-task-state|interlanguage-production|[A-Z]:[\\\\/]Users[\\\\/])", data):
                raise ValueError(f"Private workstation marker in {name}")
    return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--shims", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo, course = args.repo.resolve(), args.course.resolve()
    lock = args.lock or course / "imports.lock"
    inputs = stage_inputs(course, GitSnapshot(repo, args.ref), SourceCache(args.cache), lock,
                          args.dependencies, args.shims)
    output = args.out.resolve()
    output.mkdir(exist_ok=False, parents=True)
    for name, data in inputs.items():
        target = output / name
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_bytes(data)
    subprocess.run([sys.executable, "-B", str(output / "export_cumulative.py"), str(output)],
                   check=True)
    print(f"Staged {len(inputs)} native files and one cumulative LaTeX source")

if __name__ == "__main__":
    main()

