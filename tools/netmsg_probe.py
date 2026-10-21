import pathlib, struct, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b"\x00").decode(), base + s.VirtualAddress, s.get_data()) for s in pe.sections]
tb, td = [(sb, sd) for nm, sb, sd in secs if nm == ".text"][0]
def rd(va, n):
    for nm, sb, sd in secs:
        if sb <= va < sb + len(sd): return sd[va - sb: va - sb + n]
def dw(va, n):
    b = rd(va, 4*n); return list(struct.unpack("<%dI" % n, b)) if b else []
def sec_of(va):
    for nm, sb, sd in secs:
        if sb <= va < sb + len(sd): return nm
def find_bytes(nd):
    out = []
    for nm, sb, sd in secs:
        i = sd.find(nd)
        while i != -1:
            out.append(sb + i); i = sd.find(nd, i+1)
    return out
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def scan(fn):
    res = []; end = None
    for x in md.disasm(td[fn-tb: fn-tb+0x600], fn):
        res.append(x)
        if x.mnemonic.startswith("ret"):
            end = x.address + x.size; break
    sites = ["0x%08x" % x.address for x in res if x.mnemonic == "push" and x.op_str == "0xb"]
    return end, sites
for cls in ("SVC_SetView", "SVC_EntityMessage", "SVC_ServerInfo", "SVC_PacketEntities"):
    names = find_bytes((".?AV%s@@" % cls).encode())
    if not names: print(cls, ": not found"); continue
    tdva = names[0] - 8
    print("== %s TD 0x%08x" % (cls, tdva))
    for col in [x - 12 for x in find_bytes(struct.pack("<I", tdva))]:
        for slot in find_bytes(struct.pack("<I", col)):
            if sec_of(slot) not in (".rdata", ".data"): continue
            vt = slot + 4
            for k, v in enumerate(dw(vt, 10)):
                if sec_of(v) != ".text": continue
                end, sites = scan(v)
                if sites:
                    print("   vtable 0x%08x slot[%d] 0x%08x  end~0x%08x  push0xb: %s" % (vt, k, v, end or 0, ", ".join(sites)))
