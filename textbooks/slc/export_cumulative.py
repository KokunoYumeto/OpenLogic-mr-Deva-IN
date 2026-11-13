"""Export and restore the editable single-file Marathi SLC screen source."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


DRIVER = "slc-screen.tex"
CUMULATIVE = "slc-screen-mr.tex"
ROOT_INPUTS = ("slc.tex", "slc-config.sty", "slc-envs.sty", "slc-screen.xmpdata", "slc-metadata.tex")
SUMMARY_NUMBERS = (1, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15)
RUNTIME_LOCALE = "open-logic/locale/mr"
NATIVE_LOCALE = "locale/mr"
FILE_BEGIN = rb"\begin{filecontents*}{"
FILE_END = rb"\end{filecontents*}"
DRIVER_MARK = b"% === slc-screen.tex ==="
HEADER = """% संच, तर्कशास्त्र, संगणन — Richard Zach
% Open Logic Project च्या ग्रंथावर आधारित मराठी आवृत्ती.
% पुस्तकाचा मजकूर CC BY 4.0 परवान्याखाली उपलब्ध आहे.
% एकत्रित संपादनयोग्य LaTeX स्रोत. संकलनासाठी स्रोत-संग्रहातील
% अक्षररूपे, चित्रे, संदर्भसूची आणि Open Logic शैली आवश्यक आहेत.
% हा मजकूर संपादित करून संकलित करण्यासाठी: pwsh -File ./build.ps1 -Cumulative
""".encode("utf-8")
BUILD_ENTRYPOINT = (
    b"\\errmessage{Build this source with pwsh -File ./build.ps1 -Cumulative}\n"
    b"\\csname @@end\\endcsname\n"
)
PATH_COMPONENT = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*\Z")


def fingerprint(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_inputs(book):
    """Yield runtime destinations and their original files in a native or staged book."""
    for name in ROOT_INPUTS:
        path = book / name
        if path.is_file() or name in ROOT_INPUTS[:3]:
            yield name, path

    for name in ("preface.tex", "glossary.tex"):
        yield f"include/{name}", book / "include" / name
    for number in SUMMARY_NUMBERS:
        name = f"include/summary-{number}.tex"
        yield name, book / name
    for path in sorted((book / "include").glob("*.tex")):
        if path.name not in {"preface.tex", "glossary.tex"} and not path.name.startswith("summary-"):
            yield path.relative_to(book).as_posix(), path

    config_dir = book / NATIVE_LOCALE / "config"
    for path in sorted(config_dir.rglob("*")):
        if path.is_file() and path.suffix in {".sty", ".tex"}:
            yield path.relative_to(book).as_posix(), path

    native_styles = book / NATIVE_LOCALE / "locale"
    for path in sorted(native_styles.glob("*.sty")):
        dest = path.relative_to(book).as_posix()
        if path.name != "slc-token-overrides.sty":
            dest = f"{RUNTIME_LOCALE}/{path.name}"
            path = book / dest if (book / dest).is_file() else path
        yield dest, path

    for area in ("content", "photocredits"):
        relative = f"{RUNTIME_LOCALE}/{area}"
        directory = book / relative
        if not directory.is_dir():
            directory = book / NATIVE_LOCALE / area
        for path in sorted(directory.rglob("*.tex")):
            yield f"{relative}/{path.relative_to(directory).as_posix()}", path

    for path in sorted((book / "open-logic/assets/diagrams").rglob("*.tikz")):
        yield path.relative_to(book).as_posix(), path


def validate_path(name):
    parts = name.split("/")
    if not all(PATH_COMPONENT.fullmatch(part) for part in parts):
        raise ValueError(f"Invalid cumulative input path {name!r}")
    relative = PurePosixPath(name)
    allowed = (
        name in ROOT_INPUTS
        or (parts[0] == "include" and relative.suffix == ".tex")
        or (parts[:3] == ["locale", "mr", "config"] and relative.suffix in {".sty", ".tex"})
        or name == "locale/mr/locale/slc-token-overrides.sty"
        or (parts[:3] == ["open-logic", "locale", "mr"] and len(parts) == 4 and relative.suffix == ".sty")
        or (
            parts[:3] == ["open-logic", "locale", "mr"] and len(parts) >= 5
            and parts[3] in {"content", "photocredits"} and relative.suffix == ".tex"
        )
        or (parts[:3] == ["open-logic", "assets", "diagrams"] and relative.suffix == ".tikz")
    )
    if not allowed:
        raise ValueError(f"Unrecognized cumulative input {name!r}")


def inspect_book(book):
    inputs = {}
    for name, path in source_inputs(book):
        validate_path(name)
        data = path.read_bytes()
        data.decode("utf-8")
        if not data.endswith(b"\n") or data.startswith(b"\xef\xbb\xbf"):
            raise ValueError(f"Expected BOM-free UTF-8 with a terminal newline in {name}")
        if FILE_END in data:
            raise ValueError(f"Reserved cumulative block delimiter in {name}")
        if name in inputs:
            raise ValueError(f"Duplicate cumulative input {name}")
        inputs[name] = data

    modules = [name for name in inputs if name.startswith(f"{RUNTIME_LOCALE}/content/")]
    if len(modules) != 176:
        raise ValueError(f"Expected 176 Marathi textbook modules, found {len(modules)}")
    observed_summaries = {path.name for path in (book / "include").glob("summary-*.tex")}
    expected_summaries = {f"summary-{number}.tex" for number in SUMMARY_NUMBERS}
    if observed_summaries != expected_summaries:
        raise ValueError(f"Unexpected summary inventory: {sorted(observed_summaries)}")
    glossary = inputs["include/glossary.tex"]
    glossary_keys = re.findall(rb"(?m)^\\newglossaryentry\s*\{([^}]+)\}", glossary)
    if len(glossary_keys) != 79 or len(set(glossary_keys)) != 79:
        raise ValueError(f"Expected 79 unique glossary entries, found {len(set(glossary_keys))}")
    driver = (book / DRIVER).read_bytes()
    driver.decode("utf-8")
    if not driver.endswith(b"\n") or driver.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"Expected BOM-free UTF-8 with a terminal newline in {DRIVER}")
    return inputs, driver


def parse_cumulative(data):
    """Read raw blocks without changing whitespace, comments, or TeX syntax."""
    pending = iter(data.splitlines(keepends=True))
    inputs = {}
    in_header = True
    for line in pending:
        if line.rstrip(b"\r\n") == DRIVER_MARK:
            driver = b"".join(pending)
            if not driver:
                raise ValueError("Missing screen driver after cumulative source blocks")
            return inputs, driver
        if line.startswith(FILE_BEGIN):
            in_header = False
            if not line.rstrip(b"\r\n").endswith(b"}"):
                raise ValueError("Malformed cumulative source block")
            name = line.rstrip(b"\r\n")[len(FILE_BEGIN):-1].decode("ascii")
            validate_path(name)
            if name in inputs:
                raise ValueError(f"Duplicate cumulative input {name}")
            payload = []
            for line in pending:
                if line.rstrip(b"\r\n") == FILE_END:
                    break
                if FILE_END in line or line.startswith(FILE_BEGIN):
                    raise ValueError(f"Unterminated cumulative input {name}")
                payload.append(line)
            else:
                raise ValueError(f"Unterminated cumulative input {name}")
            inputs[name] = b"".join(payload)
        elif (
            line.strip()
            and not line.startswith(b"%")
            and not (in_header and line.replace(b"\r\n", b"\n") in BUILD_ENTRYPOINT.splitlines(keepends=True))
        ):
            raise ValueError("Unexpected text outside cumulative source blocks")
    raise ValueError("Missing screen driver marker")


def export_cumulative(book, destination):
    inputs, driver = inspect_book(book)
    blocks = [HEADER, BUILD_ENTRYPOINT, b"\n"]
    for name, data in inputs.items():
        blocks.extend((FILE_BEGIN, name.encode("ascii"), b"}\n", data, FILE_END, b"\n\n"))
    blocks.extend((DRIVER_MARK, b"\n", driver))
    output = b"".join(blocks)
    if parse_cumulative(output) != (inputs, driver):
        raise ValueError("Cumulative source does not round-trip")
    destination.write_bytes(output)
    return {
        **fingerprint(output),
        "screen_driver": fingerprint(driver),
        "embedded_inputs": {name: fingerprint(data) for name, data in inputs.items()},
    }


def extract_cumulative(source, stage, expected_paths=None):
    """Materialize the source into an isolated build stage before XeLaTeX."""
    inputs, driver = parse_cumulative(source.read_bytes())
    if expected_paths is not None and set(inputs) != set(expected_paths):
        missing = sorted(set(expected_paths) - set(inputs))
        extra = sorted(set(inputs) - set(expected_paths))
        raise ValueError(f"Cumulative source inventory differs: missing {missing}, extra {extra}")
    records = {}
    for name, data in {**inputs, DRIVER: driver}.items():
        target = stage / name
        if not target.resolve().is_relative_to(stage.resolve()):
            raise ValueError(f"Cumulative path escapes build stage: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records[name] = fingerprint(data)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=Path, help="native or staged modular book")
    parser.add_argument("output", type=Path, nargs="?", help=f"default: BOOK/{CUMULATIVE}")
    parser.add_argument("--manifest", type=Path, help="save exact cumulative source and input hashes")
    args = parser.parse_args()
    destination = args.output or args.book / CUMULATIVE
    manifest = export_cumulative(args.book, destination)
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "source": str(destination),
        "bytes": manifest["bytes"],
        "sha256": manifest["sha256"],
        "embedded_inputs": len(manifest["embedded_inputs"]),
    }))


if __name__ == "__main__":
    main()
