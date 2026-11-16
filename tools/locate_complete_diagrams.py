"""Compare a prior PDF diagram and its new location, allowing translation only."""
import argparse
import hashlib
import json
from pathlib import Path
from functools import lru_cache
import re

import fitz
import numpy as np


def coordinates(item):
    if isinstance(item, (fitz.Point, fitz.Rect)):
        return tuple(item)
    if isinstance(item, fitz.Quad):
        return tuple(v for p in item for v in p)
    return ()


def page_objects(page):
    shapes = []
    for s in page.get_drawings():
        style = tuple(s.get(k) for k in ('type','color','fill','width','dashes','even_odd','lineJoin','lineCap','closePath','fill_opacity','stroke_opacity'))
        types = tuple(tuple(i if not coordinates(i) else type(i).__name__ for i in item) for item in s['items'])
        points = [v for item in s['items'] for i in item for v in coordinates(i)]
        shapes.append((s['rect'], (style, types), np.array(points).reshape(-1,2)))
    glyphs = []
    for s in page.get_texttrace():
        style = tuple(s.get(k) for k in ('font','size','dir','wmode','type','color','opacity'))
        for char, _, origin, bbox in s['chars']:
            # Font subset indices can change. Compare the actual rendered
            # glyphs along with their Unicode, font attributes and positions.
            glyphs.append((fitz.Rect(bbox), (style,char), np.array([origin,bbox[:2],bbox[2:]])))
    return shapes, glyphs


def select(objects, box):
    return [o for o in objects if box.x0 <= (o[0].x0 + o[0].x1)/2 <= box.x1
            and box.y0 <= (o[0].y0 + o[0].y1)/2 <= box.y1]


def same(old, new, delta):
    if len(old) != len(new):
        return False
    for a,b in zip(old,new):
        if a[1] != b[1] or a[2].shape != b[2].shape or np.max(np.abs(a[2]+delta-b[2]),initial=0) > 0.025:
            return False
    return True


def pixels(page, box):
    pix = page.get_pixmap(matrix=fitz.Matrix(4,0,0,4,-4*box.x0,-4*box.y0),clip=box,alpha=False)
    return pix.width, pix.height, hashlib.sha256(pix.samples).hexdigest()


def locate(name, start, box, old_page, document, pages, candidates):
    s0,g0 = page_objects(old_page)
    shapes,glyphs = select(s0,box),select(g0,box)
    anchor = max(shapes or glyphs, key=lambda s: len(s[2]), default=None)
    if anchor is None:
        raise ValueError(name + ': no ink anchor')
    matches = []
    for pn in candidates:
        vectors,chars = pages(pn)
        for shape in (vectors if shapes else chars):
            if shape[1] != anchor[1] or not len(shape[2]):
                continue
            delta = shape[2][0] - anchor[2][0]
            if not same([anchor],[shape],delta):
                continue
            clip = fitz.Rect(*(np.array(box) + np.tile(delta,2)))
            if same(shapes, select(vectors,clip),delta) and same(glyphs,select(chars,clip),delta):
                ink = pixels(old_page, box)
                if ink == pixels(document[pn-1], clip):
                    matches.append((pn,clip,len(shapes),len(glyphs),ink[2]))
    if len(matches) > 1:
        # Identical diagrams can recur in neighboring examples. Require the
        # surrounding text or figures to correspond, too, before choosing.
        for padding in ((-12,-12,12,12),(-40,0,40,56),(-40,-56,40,0),(-72,-72,72,72)):
            padded = box + padding
            context = pixels(old_page, padded)
            candidates = [m for m in matches if pixels(document[m[0]-1], m[1]+padding) == context]
            if len(candidates) == 1:
                matches = candidates
                break
    if len(matches) != 1:
        raise ValueError(f'{name}: {len(matches)} exact translations of {len(shapes)} paths and {len(glyphs)} glyphs from page {start}')
    return matches[0]


def run(root, old_file, old_tex, page_window):
    build = root / 'build/full'
    current_file = build / 'openlogic-mr-full.pdf'
    reader_file = build / 'openlogic-mr-full.tex'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    from complete_diagram_inventory import current_inventory
    old_tex_hash = sha(old_tex)
    maps = root / "tools/diagram-maps"
    origin = json.loads((maps / (old_tex_hash + ".json")).read_bytes())
    previous_pdf_hash = sha(old_file)
    if (origin["source_tex_sha256"] != old_tex_hash or origin["source_pdf_sha256"] != previous_pdf_hash
            or origin["unresolved"]):
        raise ValueError("The previous PDF, TeX and checked diagram map must describe the same release.")
    previous = current_inventory(old_tex.read_text("utf-8"))
    now = current_inventory(reader_file.read_text('utf-8'))
    def identity(entries):
        return [{k:v for k,v in entry.items() if k!='source_line'} for entry in entries]
    if identity(previous)!=identity(now):
        raise ValueError('diagram source, labels, caption or order changed')
    inventory = {r['name']:r for r in now}
    aux = (build/'openlogic-mr-full.aux').read_text('utf-8')
    labels = dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{[^}]*\}\{(\d+)\}',aux))
    result = {'old_pdf_sha256':sha(old_file),'source_pdf_sha256':sha(current_file),'source_tex_sha256':sha(reader_file), 'matches':{},'unresolved':{}}
    with fitz.open(old_file) as baseline, fitz.open(current_file) as new:
        @lru_cache(maxsize=6)
        def objects(page):
            return page_objects(new[page-1])
        for name, row in sorted(origin["matches"].items(), key=lambda item: item[1]["page"]):
            pn = row["page"]
            box = fitz.Rect(row["rect"])
            label_pages = {int(labels[label]) for label in inventory[name].get("figure_labels", []) if label in labels}
            if len(label_pages) > 1:
                raise ValueError(f"{name}: figure labels resolve to different pages")
            candidates = label_pages or range(max(1,pn-page_window), min(len(new),pn+page_window)+1)
            if pixels(baseline[pn-1], box)[2] != row["rgb_sha256_at_288dpi"]:
                raise ValueError(f"{name}: previous render and documented crop differ")
            try:
                pg,rect,paths,glyphs,ink=locate(name,pn,box,baseline[pn-1],new,objects,candidates)
            except ValueError as err:
                result['unresolved'][name]=str(err)
                continue
            result['matches'][name]={'old_page':pn,'old_rect':list(box),'page':pg,'rect':list(rect),'paths':paths,'glyphs':glyphs,'rgb_sha256_at_288dpi':ink}
    content = (json.dumps(result, indent=2) + "\n").encode()
    if result["unresolved"]:
        (build / "unresolved-diagrams.json").write_bytes(content)
        raise ValueError("Inspect unresolved-diagrams.json in the build directory: " + ", ".join(result["unresolved"]))
    destination = maps / (result["source_tex_sha256"] + ".json")
    if destination.exists() and destination.read_bytes() != content:
        raise ValueError("A different diagram record already exists for this source; compare the two builds.")
    if not destination.exists():
        with destination.open("xb") as output:
            output.write(content)
    print(len(result["matches"]), "diagram crops verified;", destination.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-pdf", type=Path, required=True)
    parser.add_argument("--previous-tex", type=Path, required=True)
    parser.add_argument("--page-window", type=int, default=8, help="search range for figures without a LaTeX label")
    args = parser.parse_args()
    if args.page_window < 0:
        parser.error("--page-window must be nonnegative")
    run(Path(__file__).resolve().parents[1], args.previous_pdf, args.previous_tex, args.page_window)
