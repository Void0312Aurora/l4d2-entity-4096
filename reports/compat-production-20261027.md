# Production-copy compatibility repair record

Date: 2026-10-27

The test used an isolated copy of the local dedicated-server tree. The live
server directory was not started or modified. The patched Linux modules,
rebuilt SourceMod core/SDKTools/SDKHooks, the host's existing plugin tree and
84 workshop VPKs were tested together. `nextmap.smx` remained disabled because
its own SourceMod source rejects L4D2.

## Problems and repairs

* Stock SDKHooks crashed in `SDKHooks::SDK_OnLoad` while inserting an entity
  listener. The trace points to the stock Linux listener offset (`65572`) being
  read against the patched layout. The compatibility package uses the tested
  `EntityListeners=131108` override and rebuilt SourceMod core, SDKTools and
  SDKHooks; the same startup then loaded normally.
* `sm_d65_force <index>` did not force an index. The SourceMod native ignores
  the old second argument and allocates normally, so the probe now reports the
  actual index. It also skips `SDKHook` for an invalid index instead of
  throwing an exception.
* The first command rejected by `Cbuf_AddText` was
  `witch_shock_ammo_drop "100.0"` from `l4d2_specialammo.cfg`. The private
  copy keeps all 80 commands and values but loads them from eight small
  sequential files. Repeating the load after changing the value to `37.0`
  restored it to `100.0`, proving that the final chunk executes.
* Nine VPK mission entries had malformed KeyValues. The exact archive IDs and
  source/patched hashes are recorded in
  [`mission-vpk-repairs.json`](compat-production-20261027/mission-vpk-repairs.json).
  Only the affected entry was copied to the end of each private VPK and its
  directory record/CRC was updated. Originals remain available for rollback;
  the third-party archives are not committed to this repository.

## Verification

The final private copy had all 84 VPKs active. It started on `c1m1_hotel`,
reported 46 SourceMod plugins and 9 extensions, changed to
`c8m1_apartment`, and exited cleanly. The final console record had zero
`Cbuf_AddText: buffer overflow` lines and zero mission/KeyValues parse errors.
The `witch_shock_ammo_drop` value was `100.0` before and after the map change.

This validates startup, plugin loading, configuration execution and a map
transition. It does not validate two real Steam users, public/VAC operation,
or high-index behavior for every production plugin.
