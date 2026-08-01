#!/usr/bin/env python3
"""Fail when a release PNG is not 8-bit RGBA or has no transparent pixels."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
    return (left, above, upper_left)[distances.index(min(distances))]


def alpha_counts(path: Path) -> tuple[int, int, int, int]:
    payload = path.read_bytes()
    if not payload.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")

    position = len(PNG_SIGNATURE)
    header: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    while position < len(payload):
        if position + 12 > len(payload):
            raise ValueError("truncated PNG chunk")
        size = struct.unpack(">I", payload[position : position + 4])[0]
        kind = payload[position + 4 : position + 8]
        start = position + 8
        end = start + size
        if end + 4 > len(payload):
            raise ValueError("truncated PNG chunk data")
        data = payload[start:end]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            break
        position = end + 4

    if header is None:
        raise ValueError("missing IHDR")
    width, height, depth, color_type, compression, filtering, interlace = header
    if (depth, color_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
        raise ValueError(
            "expected non-interlaced 8-bit RGBA PNG "
            f"(found depth={depth}, color_type={color_type}, interlace={interlace})"
        )

    raw = zlib.decompress(bytes(compressed))
    stride = width * 4
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError(f"unexpected image data length {len(raw)} (expected {expected})")

    previous = bytearray(stride)
    offset = 0
    transparent = 0
    partial = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        encoded = raw[offset : offset + stride]
        offset += stride
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth(left, above, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            decoded[index] = (value + predictor) & 0xFF
        for alpha in decoded[3::4]:
            transparent += alpha == 0
            partial += 0 < alpha < 255
        previous = decoded
    return width, height, transparent, partial


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        try:
            width, height, transparent, partial = alpha_counts(path)
            if transparent == 0:
                raise ValueError("image has no fully transparent pixels")
            print(
                f"{path}: {width}x{height}, transparent={transparent}, "
                f"partial-alpha={partial}"
            )
        except (OSError, ValueError, zlib.error) as error:
            failed = True
            print(f"{path}: FAILED: {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
