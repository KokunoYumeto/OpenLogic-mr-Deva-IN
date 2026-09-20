"""Create labeled contact sheets and a hash manifest for rendered PDF pages."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


parser = argparse.ArgumentParser()
parser.add_argument("render_dir", type=Path)
parser.add_argument("--pages-per-sheet", type=int, default=24)
args = parser.parse_args()

render_dir = args.render_dir.resolve()
pages = sorted(render_dir.glob("page-*.png"))
assert pages, render_dir
assert args.pages_per_sheet == 24

page_records = []
for path in pages:
    with Image.open(path) as image:
        page_records.append(
            {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": image.width,
                "height": image.height,
            }
        )

contacts = []
cell_width, cell_height = 230, 335
thumb_width, thumb_height = 210, 297
columns, rows = 4, 6
for sheet_index, start in enumerate(range(0, len(pages), args.pages_per_sheet), 1):
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "white")
    draw = ImageDraw.Draw(sheet)
    for offset, path in enumerate(pages[start : start + args.pages_per_sheet]):
        with Image.open(path) as page:
            thumb = ImageOps.contain(page.convert("RGB"), (thumb_width, thumb_height))
        column, row = offset % columns, offset // columns
        x = column * cell_width + (cell_width - thumb.width) // 2
        y = row * cell_height + 25
        sheet.paste(thumb, (x, y))
        draw.rectangle((x - 1, y - 1, x + thumb.width, y + thumb.height), outline="#777777")
        draw.text((column * cell_width + 8, row * cell_height + 6), path.stem, fill="black")
    contact_path = render_dir / f"contact-{sheet_index:02d}.jpg"
    sheet.save(contact_path, quality=88, optimize=True)
    contacts.append(
        {
            "filename": contact_path.name,
            "first_page": start + 1,
            "last_page": min(start + args.pages_per_sheet, len(pages)),
            "bytes": contact_path.stat().st_size,
            "sha256": hashlib.sha256(contact_path.read_bytes()).hexdigest(),
        }
    )

manifest = {
    "schema": "openlogic-pdf-render-manifest/1",
    "source_pdf": "build/core/openlogic-mr-core.pdf",
    "page_count": len(pages),
    "render_dpi": 96,
    "pages": page_records,
    "contacts": contacts,
}
(render_dir / "RENDER_PAGES.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "pages": len(pages),
            "contacts": len(contacts),
            "first_dimensions": [page_records[0]["width"], page_records[0]["height"]],
        }
    )
)
