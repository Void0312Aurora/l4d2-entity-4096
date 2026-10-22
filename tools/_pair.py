import pathlib, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
def loads(disp):
    out = []
    for i in range(len(td) - 3):
        if td[i] != 0x8B: continue
        m = td[i+1]
        if (m & 0xC0) != 0x40 or (m & 7) == 4: continue
        if td[i+2] != disp: continue
        out.append(tb + i)
    return out
a54 = loads(0x54); a58 = loads(0x58)
print("loads [reg+0x54]:", len(a54), " [reg+0x58]:", len(a58))
pairs = []
for x in a54:
    near = [y for y in a58 if abs(y - x) <= 0xC0]
    if near:
        pairs.append((x, near))
print("adjacent-load candidates:", len(pairs))
for x, ys in pairs[:20]:
    print("   0x%08x  ~  %s" % (x, ", ".join("0x%08x" % y for y in ys[:3])))
