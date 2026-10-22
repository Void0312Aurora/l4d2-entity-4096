import pathlib, struct, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
res = {}
for disp in (0x54, 0x58):
    hits = []
    for i in range(len(td) - 4):
        if td[i] != 0xFF: continue
        m = td[i+1]
        if (m & 0xC0) != 0x40 or (m & 0x38) != 0x30 or (m & 7) == 4: continue  # push r/m32
        if td[i+2] != disp: continue
        # look ahead for call rel32 within 14 bytes
        tgt = None
        for j in range(i+3, min(i+18, len(td)-5)):
            if td[j] == 0xE8:
                rel = struct.unpack_from("<i", td, j+1)[0]
                tgt = tb + j + 5 + rel
                break
        hits.append((tb + i, tgt))
    res[disp] = hits
    print("== push [reg+0x%02x] then call: %d" % (disp, len(hits)))
    seen = set()
    for va, tgt in hits:
        key = (tgt,)
        if tgt is not None and key in seen: continue
        seen.add(key)
        print("   site 0x%08x -> call %s" % (va, ("0x%08x" % tgt) if tgt else "?"))
