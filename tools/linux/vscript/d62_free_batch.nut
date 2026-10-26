// Bound per-frame work when GDB adds substantial cost to entity destruction.
local count=0
while (::d62_fillers.len()>0 && count<64) {
    local e=::d62_fillers.pop()
    if (e.IsValid()) { e.Kill(); ++count; }
}
printl("D62_FREE_BATCH requested="+count+" remaining="+d62_fillers.len())
