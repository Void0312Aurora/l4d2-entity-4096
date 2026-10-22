import pathlib, struct, pefile
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
def callers(t):
    out = []
    i = td.find(b"\xe8")
    while i != -1:
        rel = struct.unpack_from("<i", td, i+1)[0]
        if tb + i + 5 + rel == t: out.append(tb + i)
        i = td.find(b"\xe8", i+1)
    return out
for t in (0x10091F50, 0x10091910, 0x100913E0, 0x1011CE60):
    cs = callers(t)
    print("callers of 0x%08x: %d -> %s" % (t, len(cs), " ".join("0x%08x" % x for x in cs[:10])))
