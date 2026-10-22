import pathlib, struct, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def callers(target):
    out = []
    nd = struct.pack("<i", target - (0))
    i = td.find(b"\xe8")
    while i != -1:
        rel = struct.unpack_from("<i", td, i + 1)[0]
        va = tb + i
        if va + 5 + rel == target:
            out.append(va)
        i = td.find(b"\xe8", i + 1)
    return out
for t in (0x10053F50, 0x101D7340, 0x101D7460):
    cs = callers(t)
    print("== target 0x%08x  direct callers: %d" % (t, len(cs)))
    for s in cs[:12]:
        print("   0x%08x" % s)
