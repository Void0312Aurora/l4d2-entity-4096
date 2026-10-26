#!/usr/bin/env python3
"""Relocate both client baselines without moving the CClientState object.

Uses the game's allocator once per state and frees the array in its destructor.
The new PE section contains only relative-call code and is read/execute.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile

from net_apply_13bit import pe_checksum, va_to_off


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    data = bytearray(a.source.read_bytes())
    if hashlib.sha256(data).hexdigest() != '148f602030f99bca301925626c08a2fb27755db256e8044ab037a450c4e7bed3':
        raise SystemExit('source SHA mismatch')
    address = 0x10743000
    with tempfile.TemporaryDirectory() as directory:
        obj, raw = Path(directory)/'stub.o', Path(directory)/'stub.bin'
        subprocess.run(['as', '--32', str(Path(__file__).with_name('engine_baselines.S')),
                        '-o', str(obj)], check=True)
        subprocess.run(['ld', '-m', 'elf_i386', '-Ttext', hex(address),
                        '--oformat', 'binary', str(obj), '-o', str(raw)], check=True)
        code = raw.read_bytes()

    def patch(va, old, new):
        offset = va_to_off(data, va)
        if data[offset:offset+len(old)] != old or len(old) != len(new):
            raise SystemExit(f'patch mismatch at {va:#x}')
        data[offset:offset+len(old)] = new

    def hook(va, old, stub):
        expected = bytes.fromhex(old)
        patch(va, expected, b'\xe8'+struct.pack('<i', address+stub-va-5)
              + b'\x90'*(len(expected)-5))

    hook(0x1005925b, 'e8c0af2200', 0)
    hook(0x1005220c, '8b8481e0010000', 0x80)
    hook(0x10052230, '8db481e0010000', 0x100)
    hook(0x10053450, '8d9c08e0010000', 0x180)
    hook(0x10053458, '8d8c0ae0010000', 0x200)
    hook(0x100533f7, '8db1e0010000', 0x280)
    hook(0x10058ffe, 'e84dffffff', 0x300)
    for va, old, new in [(0x10052208, b'\x0b', b'\x0c'),
                         (0x1005222d, b'\x0b', b'\x0c'),
                         (0x1005344c, b'\x0d', b'\x0e'),
                         (0x1005344f, b'\x0d', b'\x0e'),
                         (0x10053405, struct.pack('<I', 2048), struct.pack('<I', 4096)),
                         (0x10053466, struct.pack('<I', 2048), struct.pack('<I', 4096))]:
        patch(va, old, new)

    pe = struct.unpack_from('<I', data, 0x3c)[0]
    opt = pe+24
    count = struct.unpack_from('<H', data, pe+6)[0]
    header = opt+struct.unpack_from('<H', data, pe+20)[0]+40*count
    if any(data[header:header+40]) or header+40 > struct.unpack_from('<I', data, opt+60)[0]:
        raise SystemExit('no room for section header')
    if struct.unpack_from('<I', data, opt+56)[0] != address-0x10000000:
        raise SystemExit('unexpected image end')
    raw_offset = (len(data)+511)&~511
    raw_size = (len(code)+511)&~511
    struct.pack_into('<8sIIIIIIHHI', data, header, b'.clbase', len(code),
                     address-0x10000000, raw_size, raw_offset, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', data, pe+6, count+1)
    struct.pack_into('<I', data, opt+4, struct.unpack_from('<I', data, opt+4)[0]+raw_size)
    struct.pack_into('<I', data, opt+56, address-0x10000000+0x1000)
    data += bytes(raw_offset-len(data))+code+bytes(raw_size-len(code))
    cert_offset, cert_size = struct.unpack_from('<II', data, opt+128)
    struct.pack_into('<I', data, opt+64, pe_checksum(data, opt+64, cert_offset, cert_size))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(data)
    print(f'{a.output} sha256={hashlib.sha256(data).hexdigest()}')


if __name__ == '__main__':
    main()
