"""Copy the native reader inputs to a fresh directory and install its Marathi locale."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT_FILES = ('slc-screen.tex', 'slc-screen.xmpdata', 'slc.tex', 'slc-config.sty',
              'slc-envs.sty', 'slc-metadata.tex')
ROOT_DIRS = ('fonts', 'illustrations', 'include', 'open-logic', 'locale/mr', 'vendor/nowidow')
BUILD_SUFFIXES = {'.tex', '.sty', '.cls', '.tikz', '.xmpdata', '.ttf', '.otf', '.png', '.jpg',
                  '.jpeg', '.pdf', '.bib', '.bst', '.cfg', '.def', '.bbx', '.cbx', '.map', '.ldf'}
FONT_RESOURCE_LOCK = Path("fonts/SLC-MATH-RESOURCES.json")

def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def font_resources(root):
    manifest = json.loads((root / FONT_RESOURCE_LOCK).read_bytes())
    if manifest['schema'] != 'slc-math-driver-resources.v1':
        raise ValueError('Unexpected math driver resource manifest')
    resources = {Path(name): expected for name, expected in manifest['resources'].items()}
    if not resources:
        raise ValueError('Empty math driver resource manifest')
    for path, expected in resources.items():
        source = root / path
        if (path.is_absolute() or '..' in path.parts or not source.is_file() or source.is_symlink()
                or not source.resolve().is_relative_to(root.resolve()) or digest(source.read_bytes()) != expected):
            raise ValueError(f'Math driver resource is missing, unsafe or altered: {path}')
    return resources


def copy_inputs(root, stage, selected):
    records = {}
    resources = font_resources(root)

    def put(source, dest):
        if not source.is_file() or source.is_symlink():
            raise ValueError(f'Input missing or symlink: {source}')
        data = source.read_bytes()
        output = stage / dest
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise ValueError(f'Conflicting input: {dest}')
        output.write_bytes(data)
        records[str(dest).replace('\\', '/')] = digest(data)

    for path in resources:
        if path.parts[0] != 'fonts':
            put(root / path, path)

    for name in ROOT_FILES:
        source = root / name
        if name in {'slc-screen.xmpdata', 'slc-metadata.tex'} and not source.exists():
            continue
        put(source, name)
    if selected == 'slc-screen-mr.tex':
        put(root / selected, selected)
    for name in ROOT_DIRS:
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f'Input directory missing or symlink: {directory}')
        for source in sorted(directory.rglob('*')):
            if source.is_file() and (source.suffix.lower() in BUILD_SUFFIXES or
                                     source.relative_to(root) in resources or
                                     source.relative_to(root) == FONT_RESOURCE_LOCK):
                dest = source.relative_to(root)
                if dest.parts[:3] == ('open-logic', 'locale', 'mr'):
                    raise ValueError('The Marathi locale must have one native source tree')
                put(source, dest)
                if dest.parts[:3] == ('locale', 'mr', 'locale') and source.name != 'slc-token-overrides.sty':
                    put(source, Path('open-logic/locale/mr').joinpath(*dest.parts[3:]))
                if dest.parts[:3] in {('locale', 'mr', 'content'), ('locale', 'mr', 'photocredits')}:
                    put(source, Path('open-logic').joinpath(dest))
    put(root / 'vendor/nowidow/nowidow.sty', 'nowidow.sty')
    for path, expected in resources.items():
        if records.get(path.as_posix()) != expected:
            raise ValueError(f'Math driver resource was not staged exactly: {path}')
    if FONT_RESOURCE_LOCK.as_posix() not in records:
        raise ValueError('Math driver resource manifest was not staged')
    if selected == 'slc-screen-mr.tex':
        from export_cumulative import extract_cumulative, inspect_book
        records.update(extract_cumulative(stage / selected, stage, expected_paths=inspect_book(root)[0]))
    if len(list((stage / 'open-logic/locale/mr/content').rglob('*.tex'))) != 176:
        raise ValueError('The native Marathi textbook scope must have 176 modules')
    if len(list((stage / 'include').glob('summary-*.tex'))) != 12:
        raise ValueError('The Marathi textbook must have 12 summaries')
    if not all((stage / 'include' / f'{name}.tex').is_file() for name in ('preface', 'glossary')):
        raise ValueError('The Marathi preface or glossary is missing')
    (stage / 'INPUTS.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'build_inputs': len(records), 'source': selected, 'modules': 176, 'summaries': 12}))

if __name__ == '__main__':
    _, source, destination, selected = sys.argv
    if selected not in {'slc-screen.tex', 'slc-screen-mr.tex'}:
        raise ValueError(f'Unexpected entrypoint: {selected}')
    stage = Path(destination).resolve()
    if not stage.is_dir() or any(stage.iterdir()):
        raise ValueError('The build staging directory must be empty')
    copy_inputs(Path(source).resolve(), stage, selected)
