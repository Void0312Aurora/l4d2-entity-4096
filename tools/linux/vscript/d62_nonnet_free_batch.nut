local count=0
while (::d62_nonnet_rotation.len()>0 && count<64) {
    local e=::d62_nonnet_rotation.pop()
    if (e.IsValid()) { e.Kill(); ++count; }
}
printl("D62_NONNET_FREE_BATCH requested="+count+" remaining="+d62_nonnet_rotation.len())
