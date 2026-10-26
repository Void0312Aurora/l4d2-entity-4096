#!/usr/bin/env python3
"""Read actual CClientEntityList slots from a running patched PE client.

Read-only; may need sudo because of ptrace restrictions. Coordinates are bound
to build 23990068 and the .clentls layout. m_vecOrigin is at complete-object
+0x124, verified from RecvProp registration at client.dll+0x4B269.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import time

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('pid', type=int)
ap.add_argument('indices', nargs='*', type=int, default=[0, 1, 2048, 2049, 4095])
ap.add_argument('--out', type=Path)
a = ap.parse_args()
maps = Path(f'/proc/{a.pid}/maps').read_text().splitlines()
module = next(line.split(maxsplit=5) for line in maps
              if line.endswith('/left4dead2/bin/client.dll') and line.split()[2] == '00000000')
base = int(module[0].split('-')[0], 16)
fd = os.open(f'/proc/{a.pid}/mem', os.O_RDONLY)


def read(addr, count):
    data = os.pread(fd, count, addr)
    if len(data) != count:
        raise ValueError(f'short read at {addr:#x}')
    return data


def u32(addr):
    return struct.unpack('<I', read(addr, 4))[0]


try:
    entlist = u32(base+0x6C50AC)
    if entlist != base+0x963000:
        raise SystemExit(f'expected relocated list, got {entlist:#x}')
    report = dict(pid=a.pid, time=time.time(), client_base=hex(base),
                  client_sha256=hashlib.sha256(Path(module[5]).read_bytes()).hexdigest(),
                  entity_list=hex(entlist), slots=[])
    for index in a.indices:
        if not 0 <= index < 8192:
            raise SystemExit('index outside relocated list')
        ptr, serial, nxt, prev = struct.unpack('<IIII', read(entlist+4+16*index, 16))
        row = dict(index=index, pointer=hex(ptr), serial=serial)
        if ptr:
            try:
                vt = u32(ptr)
                col = u32(vt-4)
                offset = u32(col+4)
                td = u32(col+12)
                name = read(td+8, 160).split(b'\0', 1)[0].decode('ascii', 'replace')
                complete = ptr-offset
                row.update(vtable=hex(vt), rtti=name, complete_object=hex(complete),
                           origin=struct.unpack('<fff', read(complete+0x124, 12)))
            except (OSError, ValueError) as error:
                row['read_error'] = str(error)
        report['slots'].append(row)
    text = json.dumps(report, indent=2)+'\n'
    if a.out:
        a.out.write_text(text)
    print(text, end='')
finally:
    os.close(fd)
