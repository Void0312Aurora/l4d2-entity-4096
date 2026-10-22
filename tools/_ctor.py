import pathlib, struct, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for vt in (0x103584DC, 0x1035819C, 0x10358294):
    nd = struct.pack("<I", vt)
    sites = []
    i = td.find(nd)
    while i != -1:
        sites.append(tb + i)
        i = td.find(nd, i + 4)
    print("== vftable 0x%08x : %d imm32 refs" % (vt, len(sites)))
    for s in sites[:12]:
        start = max(tb, s - 20)
        print("  site 0x%08x:" % s)
        for ins in md.disasm(td[start-tb: s + 8 - tb], start):
            print("     %08x  %-9s %s" % (ins.address, ins.mnemonic, ins.op_str))
