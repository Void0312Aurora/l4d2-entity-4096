#!/usr/bin/env python3
"""Relocate the two 2048-entry packed-entity caches to 4096-entry BSS arrays.

Pinned singleton is at ELF VA 0x3A2840. Reuse the PT_NOTE header for a
separate RW PT_LOAD (no writable code); keep the GNU note in its section.
All consumers below were decoded in CFrameSnapshotManager methods with IDA.
"""
import hashlib,struct,sys
from pathlib import Path
source,output=map(Path,sys.argv[1:3])
d=bytearray(source.read_bytes())
if hashlib.sha256(d).hexdigest()!='4dd5101be554f0030ba0a251096981c1598002113c7f957642db421161ccee01':
 raise SystemExit('source SHA mismatch')
base=0x410000-0x3a2840
sites=[(0x1e186a,0x9c,base),(0x1e1877,0x209c,base+0x4000),
       (0x1e18e5,0x9c,base),(0x1e18f2,0x209c,base+0x4000),
       (0x1e1e41,0x9c,base),(0x1e2485,0x9c,base),
       (0x1e24aa,0x9c,base),(0x1e24b7,0x209c,base+0x4000),
       (0x1e2d0a,0x9c,base),(0x1e1f11,0x2000,0x8000),(0x1e2d12,0x2000,0x8000),
       (0xe9d0a,0x800,0x1000),(0xebd14,0x800,0x1000)]
for off,old,new in sites:
 if struct.unpack_from('<I',d,off)[0]!=old:raise SystemExit(f'site mismatch {off:#x}')
 struct.pack_into('<I',d,off,new)
phoff=struct.unpack_from('<I',d,28)[0]
ph=phoff+3*32
if struct.unpack_from('<I',d,ph)[0]!=4:raise SystemExit('expected PT_NOTE slot')
end=(len(d)+0xfff)&~0xfff
struct.pack_into('<8I',d,ph,1,end,0x410000,0x410000,0,0x8000,6,0x1000)
# PT_LOAD entries must be in virtual address order. Put this RW load after
# the 0x400000 RX stub load, and move that RX header into the old note slot.
rx=bytes(d[phoff+8*32:phoff+9*32]);rw=bytes(d[ph:ph+32])
d[ph:ph+32]=rx;d[phoff+8*32:phoff+9*32]=rw
d+=bytes(end-len(d))
output.write_bytes(d)
print(f'{output} sites={len(sites)} sha256={hashlib.sha256(d).hexdigest()}')
