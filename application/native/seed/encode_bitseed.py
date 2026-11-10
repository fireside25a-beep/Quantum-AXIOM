#!/usr/bin/env python3
"""Offline seed encoding for the native, independently built decoder."""
import argparse
from pathlib import Path
import struct

def encode(raw):
    if not 1 <= len(raw) <= 16384:
        raise ValueError('bit-seed image length must be 1..16384')
    digest = 0x811c9dc5
    for b in raw:
        digest = ((digest ^ b) * 0x1000193) & 0xffffffff
    lane = bytes(int(f'{b ^ 0xa5:08b}'[::-1], 2) for b in raw)
    return b'BSTBIT01' + struct.pack('<II', len(raw), digest) + lane * 3

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.write_bytes(encode(a.image.read_bytes()))
