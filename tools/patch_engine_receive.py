#!/usr/bin/env python3
"""Expand the PE client's receive frames and high-index bounds.

Input is the reproduced storage + N4-S + 13-bit image. Every operand was
decoded with IDA; no global immediate replacement is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from net_apply_13bit import pe_checksum, va_to_off


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    data = bytearray(a.source.read_bytes())
    expected = '37ccc4caf31fdc3e91d4b6c06a47ad5701bb1ea107f3e3fe77a1d114cf2e1fde'
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('source SHA mismatch')
    sites = json.loads(Path(__file__).with_name('engine_receive_sites.json').read_text())
    for site in sites:
        offset = va_to_off(data, int(site['va'], 16))
        old, new = bytes.fromhex(site['old']), bytes.fromhex(site['new'])
        if data[offset:offset+len(old)] != old or len(old) != len(new):
            raise SystemExit(f'patch mismatch at {site["va"]}')
        data[offset:offset+len(old)] = new
    opt = struct.unpack_from('<I', data, 0x3c)[0] + 24
    cert_offset, cert_size = struct.unpack_from('<II', data, opt+128)
    struct.pack_into('<I', data, opt+64,
                     pe_checksum(data, opt+64, cert_offset, cert_size))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(data)
    print(f'{a.output} sites={len(sites)} sha256={hashlib.sha256(data).hexdigest()}')


if __name__ == '__main__':
    main()
