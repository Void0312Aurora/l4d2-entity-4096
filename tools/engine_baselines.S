/* Per-CBaseClientState [2][4096] baseline pointer arrays.
 * The former inline array's first dword now owns the heap allocation.
 * All calls are relative, so no additional PE base relocations are needed.
 */
.intel_syntax noprefix
.section .text
.global _start
.set allocate, 0x101ae9b0
.set release, 0x101ae9d0
.set zero_memory, 0x10284220
.set clear_baselines, 0x100533f0
.set destroy_address, 0x10058f50
_start:
    push 0x8000
    call allocate
    add esp, 4
    test eax, eax
    jnz 1f
    int3
1:  mov [esi+0x1e0], eax
    push 0x8000
    push 0
    push eax
    call zero_memory
    add esp, 12
    ret
.org 0x80
get_baseline:
    push ecx
    mov ecx, [ecx+0x1e0]
    mov eax, [ecx+eax*4]
    pop ecx
    ret
.org 0x100
set_baseline:
    mov esi, [ecx+0x1e0]
    lea esi, [esi+eax*4]
    ret
.org 0x180
copy_destination:
    mov ebx, [ecx+0x1e0]
    add ebx, eax
    ret
.org 0x200
copy_source:
    mov ecx, [ecx+0x1e0]
    add ecx, edx
    ret
.org 0x280
clear_array:
    mov esi, [ecx+0x1e0]
    ret
.org 0x300
destroy_array:
    call destroy_address
    push eax
    mov ecx, esi
    call clear_baselines
    push dword ptr [esi+0x1e0]
    call release
    add esp, 4
    mov dword ptr [esi+0x1e0], 0
    pop eax
    ret
