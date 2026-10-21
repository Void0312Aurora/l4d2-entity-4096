#!/usr/bin/env python3
"""CGlobalEntityList reference graph + handle-op first-pass classification.
Read-only. Emits CSV to stdout; no file in the game install is touched."""
import struct, csv, sys

from config import require, SERVER_DLL, OUT
DLL = require(SERVER_DLL)
BASE=0x10000000; OBJ=0x107E0760; ARR=0x107E0764
d=open(DLL,'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]; coff=e+4
nsec=struct.unpack_from('<H',d,coff+2)[0]; osz=struct.unpack_from('<H',d,coff+16)[0]
opt=coff+20
secs=[]
for i in range(nsec):
    b=opt+osz+i*40
    nm=d[b:b+8].rstrip(b'\0').decode(); vsz,va,rs,pr=struct.unpack_from('<IIII',d,b+8)
    secs.append((nm,va,vsz,rs,pr))
def vo(va):
    r=va-BASE
    for nm,v,vsz,rs,pr in secs:
        if v<=r<v+max(vsz,rs): return pr+(r-v)
def va_of(off):
    for nm,v,vsz,rs,pr in secs:
        if pr<=off<pr+rs: return BASE+v+(off-pr)
TEXT=[s for s in secs if s[0]=='.text'][0]; T0=BASE+TEXT[1]; T1=T0+TEXT[2]
def inside_text(va): return T0<=va<T1

listload=struct.pack('<I',OBJ)
load_sites=[]
i=TEXT[4]
while True:
    i=d.find(b'\xb9'+listload,i)
    if i<0: break
    load_sites.append(va_of(i)); i+=1
load_sites.sort()
import bisect
def nearest_list_load(va, window=0x600):
    k=bisect.bisect_left(load_sites, va-1)
    if k==0: return None
    cand=load_sites[k-1]
    if va-cand<=window:
        # reject if a RET sits between
        seg=d[vo(cand):vo(va)]
        if b'\xc3' not in seg: return cand
    return None

rows=[]
def scan(pat, cls, desc, mask=None):
    i=TEXT[4]; out=[]
    while True:
        i=d.find(pat,i)
        if i<0: break
        va=va_of(i)
        if inside_text(va):
            out.append(va)
        i+=1
    return out

def emit(vas, cls, desc):
    for va in vas:
        near=nearest_list_load(va)
        ctx=d[vo(va)-12:vo(va)+8].hex(' ')
        rows.append(dict(cls=cls, va=f"0x{va:08X}", list_func=("0x%08X"%near) if near else "",
                         ctx=ctx, desc=desc))

# H1 encode: shl reg,0xC
for op,name in [(b'\xc1\xe0\x0c','eax'),(b'\xc1\xe1\x0c','ecx'),(b'\xc1\xe2\x0c','edx'),
                (b'\xc1\xe3\x0c','ebx'),(b'\xc1\xe5\x0c','ebp'),(b'\xc1\xe6\x0c','esi'),(b'\xc1\xe7\x0c','edi')]:
    emit(scan(op,None,None), 'H1_shl12', f'shl {name},0xC')
# H2 index mask 0xFFF
emit(scan(b'\x25\xff\x0f\x00\x00',None,None),'H2_and0FFF','and eax,0xFFF')
for modrm,name in [(b'\x81\xe1','ecx'),(b'\x81\xe2','edx'),(b'\x81\xe3','ebx'),(b'\x81\xe6','esi'),(b'\x81\xe7','edi')]:
    emit(scan(modrm+b'\xff\x0f\x00\x00',None,None),'H2_and0FFF',f'and {name},0xFFF')
# H3 serial decode / mask
emit(scan(b'\x25\xff\x7f\x00\x00',None,None),'H3_and0x7FFF','and eax,0x7FFF')
for modrm,name in [(b'\x81\xe1','ecx'),(b'\x81\xe2','edx'),(b'\x81\xe6','esi')]:
    emit(scan(modrm+b'\xff\x7f\x00\x00',None,None),'H3_and0x7FFF',f'and {name},0x7FFF')
for op,name in [(b'\xc1\xe8\x0c','eax'),(b'\xc1\xe9\x0c','ecx'),(b'\xc1\xea\x0c','edx'),(b'\xc1\xee\x0c','esi')]:
    emit(scan(op,None,None),'H3_shr12',f'shr {name},0xC')
# H6 range check vs 0x1000
emit(scan(b'\x3d\x00\x10\x00\x00',None,None),'H6_cmp0x1000','cmp eax,0x1000')
for modrm,name in [(b'\x81\xf9','ecx'),(b'\x81\xfa','edx'),(b'\x81\xfe','esi'),(b'\x81\xff','edi'),(b'\x81\xf8','eax')]:
    emit(scan(modrm+b'\x00\x10\x00\x00',None,None),'H6_cmp0x1000',f'cmp {name},0x1000')

w=csv.DictWriter(sys.stdout, fieldnames=['cls','va','list_func','ctx','desc'])
w.writeheader(); [w.writerow(r) for r in rows]

# summary to stderr
import collections
cnt=collections.Counter((r['cls'], bool(r['list_func'])) for r in rows)
demo=collections.Counter(r['cls'] for r in rows)
print("\n\n# SUMMARY", file=sys.stderr)
for k in sorted(demo):
    a=sum(v for (c,f),v in cnt.items() if c==k and f)
    print(f"# {k:14s} total={demo[k]:5d}  list-related={a:4d}  undecided={demo[k]-a:5d}", file=sys.stderr)
