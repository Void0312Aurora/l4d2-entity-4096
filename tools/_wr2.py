import pathlib, pefile, capstone
p = pathlib.Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
pe = pefile.PE(str(p), fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\x00").decode(): (base + s.VirtualAddress, s.get_data()) for s in pe.sections}
tb, td = secs[".text"]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
S = 0x101d7340; L = 0x120
for ins in md.disasm(td[S-tb:S-tb+L], S):
    t = "%08x  %-9s %s" % (ins.address, ins.mnemonic, ins.op_str)
    if ins.mnemonic in ("push", "call", "and", "shr", "test", "jmp", "je", "jne", "mov") and (
        ins.mnemonic in ("push", "call", "shr")
        or "+ 0x5" in ins.op_str or "+ 0x6" in ins.op_str or "+ 0x50" in ins.op_str or "+ 0x54" in ins.op_str):
        print(t)
