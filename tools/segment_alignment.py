"""Keep blank-line segment bounds tied to the original UTF-8 file bytes."""

import hashlib
import re


def block_bounds(text):
    """Locate the legacy blank-line blocks in the original decoded file."""
    bounds = []
    position = 0
    for block in re.split(r"\n\s*\n", text.strip()):
        start = text.index(block, position)
        position = start + len(block)
        bounds.append((start, position))
    return bounds


def block_span(text, bounds, indices):
    """Return line limits and the SHA-256 of one contiguous raw block span."""
    if not indices or any(type(index) is not int for index in indices):
        raise ValueError("Segment block indices must be a nonempty integer sequence")
    first, last = indices[0], indices[-1]
    if (
        not 1 <= first <= last <= len(bounds)
        or len(indices) != last - first + 1
        or any(index != first + offset for offset, index in enumerate(indices))
    ):
        raise ValueError("Segment block indices must be ordered, contiguous, and within the file")
    start, end = bounds[first - 1][0], bounds[last - 1][1]
    return (
        text.count("\n", 0, start) + 1,
        text.count("\n", 0, end) + 1,
        hashlib.sha256(text[start:end].encode("utf-8")).hexdigest(),
    )
