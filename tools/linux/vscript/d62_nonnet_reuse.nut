// The non-network pool is FIFO. Rotate real objects through its remaining free
// nodes so the removed node is allocated again by the normal game path.
::d62_nonnet_rotation <- []
while (d62_nonnet_rotation.len()<::n27_nonnet_alloc_count) {
    local e=SpawnEntityFromTable("logic_relay", {targetname="n27_d62_rotation"})
    if (!e) throw "D62 non-network rotation exhausted unexpectedly"
    d62_nonnet_rotation.append(e)
}
::d62_nonnet_new <- d62_nonnet_rotation.top()
printl("D62_NONNET_ROTATION count="+d62_nonnet_rotation.len()+" old_valid="+d62_nonnet.IsValid()+" new_valid="+d62_nonnet_new.IsValid())
// Acceptance requires GDB to show the final allocation reused the removed slot.
