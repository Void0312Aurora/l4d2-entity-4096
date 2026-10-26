#!/usr/bin/env python3
"""Complete high-index transmit gates for the pinned Linux binaries.

CheckTransmit rejects indices above 2047 even with the expanded engine.
WriteDeltaEntities also has 18 inline 64-word iteration terminators. Their
indices are in [0,128], and only ZF is used, so cmp al,128 + nop preserves
instruction length without the sign extension of cmp eax,imm8.
"""
import argparse
import hashlib
import json
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('kind', choices=['engine','server'])
ap.add_argument('source',type=Path)
ap.add_argument('output',type=Path)
a=ap.parse_args()
expected={'engine':'5e847fd88d59645f22edfae523a586b442d48f852986701f0f3dfdc75bcb4f03',
          'server':'c59ebc75b3cfcb3b6b057aea3bb04131b90258b13dc0ce8968e7deff599c9270'}
d=bytearray(a.source.read_bytes())
if hashlib.sha256(d).hexdigest()!=expected[a.kind]:
 raise SystemExit('source SHA mismatch')
if a.kind=='engine':
 sites=json.loads((Path(__file__).resolve().parents[2]/'data/linux/d49_bitmap_end_sites.json').read_text())
else:
 sites=[dict(va='0x6b6afb',old='6681f9ff07',new='6681f9ff0f')]
for site in sites:
 off=int(site['va'],16)
 old,new=bytes.fromhex(site['old']),bytes.fromhex(site['new'])
 if d[off:off+len(old)]!=old or len(old)!=len(new):
  raise SystemExit(f'patch mismatch at {off:#x}')
 d[off:off+len(old)]=new
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_bytes(d)
print(f'{a.kind} sites={len(sites)} sha256={hashlib.sha256(d).hexdigest()} output={a.output}')
