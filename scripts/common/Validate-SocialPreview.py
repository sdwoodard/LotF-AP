#!/usr/bin/env python3
"""Validate the GitHub social-preview dimensions and upload size."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def jpeg_size(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if not payload.startswith(b"\xff\xd8"):
        raise ValueError("not a JPEG file")
    offset = 2
    while offset + 4 <= len(payload):
        if payload[offset] != 0xFF:
            offset += 1
            continue
        marker = payload[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(payload):
            break
        length = struct.unpack(">H", payload[offset : offset + 2])[0]
        if length < 2 or offset + length > len(payload):
            raise ValueError("invalid JPEG segment")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 7:
                raise ValueError("invalid JPEG frame")
            height, width = struct.unpack(">HH", payload[offset + 3 : offset + 7])
            return width, height
        offset += length
    raise ValueError("JPEG frame dimensions not found")


def main() -> int:
    path = Path(sys.argv[1])
    size = path.stat().st_size
    width, height = jpeg_size(path)
    if (width, height) != (1280, 640):
        raise SystemExit(f"{path}: expected 1280x640, found {width}x{height}")
    if size >= 1_000_000:
        raise SystemExit(f"{path}: expected less than 1 MB, found {size} bytes")
    print(f"{path}: {width}x{height}, {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
