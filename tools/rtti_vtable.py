import pathlib, struct, pefile
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b"\x00").decode(errors="replace"), base + s.VirtualAddress, s.get_data()) for s in pe.sections]
def rd(va, n):
    for name, sb, sd in secs:
        if sb <= va < sb + len(sd):
            return sd[va - sb: va - sb + n]
def dw(va, n):
    b = rd(va, 4 * n)
    return list(struct.unpack("<%dI" % n, b)) if b else []
def sec_of(va):
    for name, sb, sd in secs:
        if sb <= va < sb + len(sd):
            return name
TD = 0x104253a4
for col in (0x10412620, 0x10412648):
    print("COL 0x%08x: %s" % (col, ["0x%08x" % x for x in dw(col, 6)]))
    needle = struct.pack("<I", col)
    for name, sb, sd in secs:
        i = sd.find(needle)
        while i != -1:
            if i % 4 == 0 and name in (".rdata", ".data"):
                slot = sb + i
                vt = slot + 4
                vals = dw(vt, 10)
                print("  vftable-ptr slot 0x%08x (%s) -> vtable 0x%08x" % (slot, name, vt))
                for k, v in enumerate(vals):
                    print("    [%d] 0x%08x %s" % (k, v, sec_of(v)))
            i = sd.find(needle, i + 4)
