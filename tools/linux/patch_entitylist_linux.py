#!/usr/bin/env python3
"""Expand the pinned Linux server entity list to 4096 network + 4095 non-network slots.

The list object is moved to a new zero-filled BSS range so growing its CEntInfo
array does not overwrite adjacent globals.  This is intentionally version-bound
to the D49/D50 server candidate and checks every original byte before patching.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "18407a811c64593835907dc36395d123858aa69e73f6a651824a302c5f601a81"
OLD_BASE, OLD_SIZE = 0xFBB140, 0x10038
NEW_BASE, NEW_SIZE = 0x1060000, 0x20038
ARRAY_END = 0x10004
NEW_ARRAY_END = 0x20004


def need(ok, message):
    if not ok:
        raise SystemExit(message)


def read_sections(data):
    shoff = struct.unpack_from("<I", data, 32)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 46)[0], struct.unpack_from("<H", data, 48)[0], struct.unpack_from("<H", data, 50)[0]
    shstr = struct.unpack_from("<IIIIIIIIII", data, shoff + shstrndx * shentsize)
    names = data[shstr[4]:shstr[4] + shstr[5]]
    sections = []
    for i in range(shnum):
        ent = shoff + i * shentsize
        s = struct.unpack_from("<IIIIIIIIII", data, ent)
        end = names.find(b"\0", s[0])
        name = names[s[0]:end].decode("ascii", "replace")
        sections.append((name, ent, s))
    return sections


def vaddr_to_file(segments, va):
    for p_type, p_off, p_va, _, p_filesz, _, _, _ in segments:
        if p_type == 1 and p_va <= va < p_va + p_filesz:
            return p_off + (va - p_va)
    return None


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} SOURCE OUTPUT")
    source, output = map(Path, sys.argv[1:])
    data = bytearray(source.read_bytes())
    need(hashlib.sha256(data).hexdigest() == SOURCE_SHA, "source SHA mismatch")

    handle = json.loads((ROOT / "data/linux/entitylist_handle_sites.json").read_text())
    members = json.loads((ROOT / "data/linux/entitylist_member_sites.json").read_text())
    need(handle["binary_sha256"] == SOURCE_SHA, "handle-site manifest SHA mismatch")
    need(members["binary_sha256"] == SOURCE_SHA, "member-site manifest SHA mismatch")

    phoff = struct.unpack_from("<I", data, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 42)
    segments = [struct.unpack_from("<IIIIIIII", data, phoff + i * phentsize) for i in range(phnum)]
    sections = read_sections(data)
    by_name = {name: (ent, s) for name, ent, s in sections}
    need(".bss" in by_name and ".rel.dyn" in by_name and ".symtab" in by_name,
         "required ELF sections not found")
    bss_ent, bss = by_name[".bss"]
    need(bss[3] <= OLD_BASE and OLD_BASE + OLD_SIZE <= bss[3] + bss[5],
         "old entity-list object is outside .bss")
    need(NEW_BASE >= bss[3] + bss[5], "new entity-list address overlaps existing .bss")
    need(NEW_BASE + NEW_SIZE < 0xFFFFFFFF, "new object address overflow")

    applied = []
    seen = set()

    def patch_va(va, old_hex, new_hex, label):
        old, new = bytes.fromhex(old_hex), bytes.fromhex(new_hex)
        need(len(old) == len(new), f"size-changing patch is unsupported: {label}")
        need(va not in seen, f"duplicate patch address {va:#x}: {label}")
        need(data[va:va + len(old)] == old,
             f"byte mismatch at {va:#x} ({label}): got {data[va:va + len(old)].hex()}, expected {old.hex()}")
        data[va:va + len(old)] = new
        seen.add(va)
        applied.append((va, label))

    for site in handle["patches"]:
        patch_va(site["va"], site["old"], site["new"], site["kind"] + ":" + site["name"])
    for site in members["patches"]:
        patch_va(site["va"], site["old"], site["new"], "member:" + site["name"])

    # These sites are not direct global references, so the xref-derived manifest
    # intentionally does not include them.  Each is tied to its owning method.
    extras = [
        (0x43A3E5, "00100000", "00200000", "CBaseEntityList ctor slot count"),
        (0x43A454, "14800000", "14000100", "CBaseEntityList ctor non-network pool start"),
        (0x43A47C, "f07f0000", "f0ff0000", "CBaseEntityList ctor non-network pool bytes"),
        (0x43A4E0, "0c", "0d", "AddEntityAtSlot handle serial shift"),
        (0x43A66E, "0c", "0d", "RemoveEntityAtSlot handle serial shift"),
        (0x43A6BD, "ff070000", "ff0f0000", "RemoveEntityAtSlot network boundary"),
        (0x43A779, "ff0f0000", "ff1f0000", "RemoveEntity handle index mask"),
        (0x5EF9FA, "0c", "0d", "SetRefEHandle serial extraction"),
        (0x66DCCC, "0c", "0d", "GlobalEntityList Clear handle pack"),
        (0x66DCD8, "0c", "0d", "GlobalEntityList Clear serial extraction"),
        (0x66DCDB, "ff0f0000", "ff1f0000", "GlobalEntityList Clear index mask"),
        (0x67085C, "ff0f0000", "ff1f0000", "GetIServerEntity index mask"),
        (0x670862, "ff070000", "ff0f0000", "GetIServerEntity network bound"),
        (0x67087F, "0c", "0d", "GetIServerEntity serial pack"),
        (0x67088A, "00f03f00", "00e07f00", "GetIServerEntity serial compare"),
        (0xB1B0BB, "ff070000", "ff0f0000", "UTIL_EntityByIndex network boundary"),
        (0x4B0452, "0c", "0d", "SoundCreate handle serial pack 1"),
        (0x4B05DC, "0c", "0d", "SoundCreate handle serial pack 2"),
        (0x4B078C, "0c", "0d", "SoundCreate handle serial pack 3"),
        (0x4B0932, "0c", "0d", "SoundCreate handle serial pack 4"),
        (0x4B0ABD, "0c", "0d", "SoundCreate handle serial pack 5"),
    ]
    for va, old, new, label in extras:
        patch_va(va, old, new, label)

    # Relocate all file-backed R_386_RELATIVE addends pointing into gEntList.
    rel_ent, rel = by_name[".rel.dyn"]
    rel_count = 0
    need(rel[9] == 8, ".rel.dyn entry size is not 8")
    for off in range(rel[4], rel[4] + rel[5], rel[9]):
        r_offset, r_info = struct.unpack_from("<II", data, off)
        if (r_info & 0xFF) != 8:
            continue
        file_off = vaddr_to_file(segments, r_offset)
        if file_off is None or file_off + 4 > len(data):
            continue  # Zero-initialized BSS addends cannot point at this object.
        value = struct.unpack_from("<I", data, file_off)[0]
        if OLD_BASE <= value < OLD_BASE + OLD_SIZE:
            relative = value - OLD_BASE
            if relative >= ARRAY_END:
                relative += NEW_ARRAY_END - ARRAY_END
            struct.pack_into("<I", data, file_off, NEW_BASE + relative)
            rel_count += 1
    need(rel_count == 587, f"unexpected entity-list relocation count: {rel_count}")

    # Update the ELF symbol table's local object size/address for analysis tools.
    sym_ent, sym = by_name[".symtab"]
    strtab = sections[sym[6]][2]
    strings = data[strtab[4]:strtab[4] + strtab[5]]
    symbol_count = 0
    for off in range(sym[4], sym[4] + sym[5], sym[9]):
        name_off, value, size = struct.unpack_from("<III", data, off)
        end = strings.find(b"\0", name_off)
        name = strings[name_off:end].decode("utf8", "replace") if 0 <= name_off < len(strings) else ""
        if name == "gEntList" and value == OLD_BASE and size == OLD_SIZE:
            struct.pack_into("<II", data, off + 4, NEW_BASE, NEW_SIZE)
            symbol_count += 1
    need(symbol_count == 1, f"expected one gEntList symbol, found {symbol_count}")

    # Extend the existing RW PT_LOAD and .bss section through the moved object.
    new_mem_end = NEW_BASE + NEW_SIZE
    _, rw_index = max((p[2] + p[5], i) for i, p in enumerate(segments) if p[0] == 1 and p[6] & 2)
    rw_ph = phoff + rw_index * phentsize
    rw = segments[rw_index]
    need(rw[2] <= bss[3] < rw[2] + rw[5], "RW PT_LOAD does not contain .bss")
    struct.pack_into("<I", data, rw_ph + 20, new_mem_end - rw[2])
    struct.pack_into("<I", data, bss_ent + 20, new_mem_end - bss[3])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    report = {
        "source_sha256": SOURCE_SHA,
        "output_sha256": digest,
        "handle_sites": len(handle["patches"]),
        "member_sites": len(members["patches"]),
        "extra_sites": len(extras),
        "relocated_gEntList_addends": rel_count,
        "gEntList_old": {"address": hex(OLD_BASE), "size": hex(OLD_SIZE)},
        "gEntList_new": {"address": hex(NEW_BASE), "size": hex(NEW_SIZE)},
        "network_slots": [0, 4095],
        "reserved_slot": 4096,
        "non_network_slots": [4097, 8191],
    }
    output.with_suffix(output.suffix + ".entitylist.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
