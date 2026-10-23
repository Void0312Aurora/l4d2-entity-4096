#!/usr/bin/env python3
"""N27-D1-B/C: frame layout plus client-bitmap pointer stubs.

Builds on build_n27_frame.py, then:
  * applies the equal-length C1/C3 edits
  * appends a new RX PT_LOAD holding int 0x80 mmap2/munmap stubs
  * hooks CBaseClient ctor (0xEB3F3) and dtor (0xEB2F0) with rel32 jumps
No relocation is copied and no PLT is used: the stubs issue syscalls directly,
so the original TEXTREL instruction at 0xEB2FB stays untouched.
"""
import csv, struct, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = Path("/tmp/n27/engine_srv_n27a.so")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/n27/engine_srv_n27d1.so")

def rows(path):
    with open(REPO / path, newline="") as f:
        for r in csv.DictReader(f):
            yield r

def hb(s):
    return bytes.fromhex(s.strip())

def rel32(src_next, dst):
    return struct.pack("<i", dst - src_next)

def main():
    subprocess.check_call([sys.executable, str(REPO / "tools/linux/build_n27_frame.py"), str(BASE)])
    data = bytearray(BASE.read_bytes())

    # C1/C3 equal-length edits (skip hook rows whose new_bytes is not hex)
    applied = 0
    for r in rows("data/linux/n27b_patch_sites.csv"):
        if r.get("group") not in ("C1", "C3"):
            continue
        try:
            old, new = hb(r["old_bytes"]), hb(r["new_bytes"])
        except ValueError:
            continue
        addr = int(r["elf_addr"], 16)
        if bytes(data[addr:addr + len(old)]) != old:
            raise SystemExit(f"C edit mismatch at 0x{addr:X}")
        data[addr:addr + len(new)] = new
        applied += 1

    # stub layout: append a dedicated RX segment; move PT_NOTE out of the phdr slot
    file_size = len(data)
    stub_off = (file_size + 0xFFF) & ~0xFFF
    stub_vaddr = 0x400000

    ctor_off = 0
    ctor = bytearray()
    # mmap2(NULL,0x200,PROT_READ|WRITE,MAP_PRIVATE|ANON,-1,0) via int 0x80
    ctor += b"\x60"                                   # pushad
    ctor += b"\x31\xDB"                              # xor ebx,ebx
    ctor += b"\xB9" + struct.pack("<I", 0x200)        # mov ecx,0x200
    ctor += b"\xBA" + struct.pack("<I", 3)            # mov edx,3
    ctor += b"\xBE" + struct.pack("<I", 0x22)         # mov esi,0x22
    ctor += b"\xBF" + struct.pack("<I", 0xFFFFFFFF)   # mov edi,-1
    ctor += b"\x31\xED"                              # xor ebp,ebp
    ctor += b"\xB8" + struct.pack("<I", 192)          # mov eax,192 (mmap2)
    ctor += b"\xCD\x80"                              # int 0x80
    ctor += b"\x3D\x01\xF0\xFF\xFF"              # cmp eax,0xFFFFF001 (-4095)
    ctor += b"\x72\x02"                              # jb ok (anything below is a valid address)
    ctor += b"\x0F\x0B"                              # ud2: hard fail on -errno
    ctor += b"\x89\x44\x24\x1C"                    # mov [esp+0x1C],eax
    ctor += b"\x61"                                   # popad
    ctor += b"\x89\x83" + struct.pack("<I", 0x10C)   # mov [ebx+0x10C],eax
    ctor += b"\x89\xC2"                              # mov edx,eax
    ctor += b"\xB9" + struct.pack("<I", 0x80)        # mov ecx,0x80
    ctor += b"\x31\xC0"                              # xor eax,eax
    ctor += b"\xC3"                                  # ret
    dtor_off = len(ctor)

    dtor = bytearray()
    dtor += b"\x55\x89\xE5\x56\x53"                  # push ebp; mov ebp,esp; push esi; push ebx
    dtor += b"\x8B\x5D\x08"                          # mov ebx,[ebp+8]
    dtor += b"\x8B\x83" + struct.pack("<I", 0x10C)   # mov eax,[ebx+0x10C]
    dtor += b"\x85\xC0"                              # test eax,eax
    je_pos = len(dtor)
    dtor += b"\x74\x00"                              # je skip
    dtor += b"\x60"                                  # pushad
    dtor += b"\x89\xC3"                              # mov ebx,eax
    dtor += b"\xB9" + struct.pack("<I", 0x200)        # mov ecx,0x200
    dtor += b"\xB8" + struct.pack("<I", 91)           # mov eax,91 (munmap)
    dtor += b"\xCD\x80"                              # int 0x80
    dtor += b"\x61"                                  # popad
    dtor += b"\xC7\x83" + struct.pack("<I", 0x10C) + b"\x00\x00\x00\x00"
    skip = len(dtor)
    dtor += b"\xE9" + rel32(stub_vaddr + dtor_off + len(dtor) + 5, 0xEB2F5)
    dtor[je_pos + 1] = skip - (je_pos + 2)
    stubs = bytes(ctor) + bytes(dtor)
    note_off = (stub_off + len(stubs) + 3) & ~3
    note_vaddr = stub_vaddr + (note_off - stub_off)

    # original PT_NOTE bytes
    e_phoff = struct.unpack_from("<I", data, 28)[0]
    e_phentsize = struct.unpack_from("<H", data, 42)[0]
    e_phnum = struct.unpack_from("<H", data, 44)[0]
    note_ph = None
    for i in range(e_phnum):
        ph = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", data, ph)[0] == 4:
            note_ph = ph
            n_off = struct.unpack_from("<I", data, ph + 4)[0]
            n_sz = struct.unpack_from("<I", data, ph + 16)[0]
            note = bytes(data[n_off:n_off + n_sz])
            break
    if note_ph is None:
        raise SystemExit("PT_NOTE not found")

    data += b"\x00" * (stub_off - len(data)) + stubs + b"\x00" * (note_off - (stub_off + len(stubs))) + note

    # move PT_NOTE
    struct.pack_into("<I", data, note_ph + 4, note_off)
    struct.pack_into("<I", data, note_ph + 8, note_vaddr)
    struct.pack_into("<I", data, note_ph + 12, note_vaddr)

    # new PHDR in the freed slot at e_phoff + 8*e_phentsize
    ph = e_phoff + 8 * e_phentsize
    struct.pack_into("<IIIIIIII", data, ph,
                     1, stub_off, stub_vaddr, stub_vaddr,
                     len(stubs), len(stubs), 5, 0x1000)
    struct.pack_into("<H", data, 44, 9)

    # hooks
    ct = 0xEB3F3
    data[ct:ct + 6] = b"\xE8" + rel32(ct + 5, stub_vaddr + ctor_off) + b"\x90"
    dt = 0xEB2F0
    data[dt:dt + 5] = b"\xE9" + rel32(dt + 5, stub_vaddr + dtor_off)

    OUT.write_bytes(bytes(data))
    print(f"built {OUT}")
    print(f"stubs at file 0x{stub_off:X} vaddr 0x{stub_vaddr:X} ctor={len(ctor)} dtor={len(dtor)}")
    print(f"new LOAD at file 0x{stub_off:X} vaddr 0x{stub_vaddr:X} size={len(stubs)}; C-rows={applied}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
