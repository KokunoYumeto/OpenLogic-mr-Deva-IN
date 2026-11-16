"""Package the complete Marathi collection's editable source after a native build."""
import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def digest(data):
    return hashlib.sha256(data).hexdigest()


def public_source(path, data, approved):
    """Retain nonprinting source markers and all other bytes, including line endings."""
    used = set()
    def replace(match):
        line = match[0]
        key = digest(line)
        if key in approved:
            used.add(key)
            return approved[key].encode()
        if re.match(rb"[ \t]*%READERNOTE\{(?:SOL6-A|OL(?:FOL|INC|CMP|SIZ|AXD|COM|FUN|NOTE)-|MR(?:ARITH|SIZ|PL)-)\d+\b", line):
            raise ValueError("Unreviewed editorial comment in " + path)
        return line

    result = re.sub(rb"(?m)^[ \t]*%READERNOTE\{[^\r\n]*", replace, data)
    if used != set(approved):
        raise ValueError("Source no longer matches the comment record for " + path)
    return result


def chapter_sources(tex):
    chapters = list(re.finditer(rb"(?m)^\\chapter\{", tex))
    if len(chapters) != 79:
        raise ValueError("Expected all 79 chapters of the collection")
    end = tex.index(rb"\end{document}", chapters[-1].end())
    bounds = [m.start() for m in chapters] + [end]
    return {
        f"chapter-sources/11-openlogic-mr-chapter-{i:03}.tex": tex[start:stop]
        for i, (start, stop) in enumerate(zip(bounds, bounds[1:]), 1)
    }


def source_members(root):
    full = root / "build/full"
    native = json.loads((full / "STATIC_QA.json").read_bytes())
    tex = (full / "openlogic-mr-full.tex").read_bytes()
    if (native["represented_source_units"] != 722 or native["current_source_and_target_unit_hashes_verified"] != 722
            or native["reader_sha256"] != digest(tex) or native["unresolved_standard_reference_targets"]):
        raise ValueError("Build and verify the complete collection before packaging it")
    edition = tomllib.loads((root / "olp-edition.toml").read_text(encoding="utf-8"))
    pin = edition["pins"]["olp"]["commit"][:8]
    profile = json.loads((root / "publication/complete-source-inputs.json").read_bytes())
    paths = [*profile["inputs"], f"publication/complete-epub-{pin}.json"]
    paths.extend(p.relative_to(root).as_posix() for p in sorted((root / "tools/diagram-maps").glob("*.json"))
                 if re.fullmatch(r"[0-9a-f]{64}\.json", p.name))
    paths.extend(p.relative_to(root).as_posix() for p in sorted((root / "provenance/source-sync").glob("olp-*.json"))
                 if re.fullmatch(r"olp-[0-9a-f]{8}\.json", p.name))
    curriculum = (root / "publication/complete-source-mr.md").read_bytes()
    members = {path: (root / path).read_bytes() for path in paths}
    members.update({"README.md": curriculum, "build/full/openlogic-mr-full.tex": tex})
    members.update(chapter_sources(tex))
    ledger = [json.loads(line) for line in (root / "units.jsonl").read_bytes().splitlines()]
    if len({row["id"] for row in ledger}) != 722 or len({row["path"] for row in ledger}) != len(ledger) or len(ledger) != 722:
        raise ValueError("Incomplete unit inventory")
    targets = set()
    for row in ledger:
        source_path, target_path = "upstream/" + row["path"], "mr/" + row["path"]
        source, target = (root / source_path).read_bytes(), (root / target_path).read_bytes()
        if digest(source) != row["src_sha256"] or digest(target) != row["tr_sha256"]:
            raise ValueError("Source or translation hash changed for " + row["id"])
        public = public_source(target_path, target, profile["editorial_comments"].get(target_path, {}))
        if public != target:
            row["original_tr_sha256"], row["tr_sha256"] = row["tr_sha256"], digest(public)
        members[source_path], members[target_path] = source, public
        targets.add(target_path)
    if set(profile["editorial_comments"]) - targets:
        raise ValueError("Editorial comment record references an unknown unit")
    members["units.jsonl"] = b"".join((json.dumps(row, ensure_ascii=False) + "\n").encode() for row in ledger)
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="destination ZIP")
    args = parser.parse_args()
    members = source_members(Path(__file__).resolve().parents[1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not args.output.exists():
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(dir=args.output.parent) as directory:
            temporary = Path(directory) / "source.zip"
            with ZipFile(temporary, "x", ZIP_DEFLATED) as archive:
                for name, data in sorted(members.items()):
                    info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            # Install complete bytes under a new name, including on simultaneous invocations.
            try:
                args.output.hardlink_to(temporary)
            except FileExistsError:
                pass
    with ZipFile(args.output) as archive:
        if sorted(members) != archive.namelist() or any(archive.read(n) != data for n, data in members.items()):
            raise ValueError("The output already exists with different contents")
    print(json.dumps({"members": len(members), "sha256": digest(args.output.read_bytes())}))


if __name__ == "__main__":
    main()
