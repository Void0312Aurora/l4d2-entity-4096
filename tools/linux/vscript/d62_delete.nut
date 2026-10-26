foreach (e in ::d62_targets) {
    if (e.IsValid()) {
        local idx=e.GetEntityIndex()
        e.Kill()
        printl("D62_KILL_REQUEST idx="+idx+" immediate_valid="+e.IsValid())
    }
}
// Keep old references to query their validity after the frame cleanup.
