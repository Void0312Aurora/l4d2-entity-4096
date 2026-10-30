# Runtime entity-index evidence

This directory preserves the controlled runtime test on `c6m1_riverbank`.

- The server was the patched Linux 4096 build, with `sv_cheats` restored to `0` after each scan.
- `z_common_limit` was set to `500`; this only permitted a larger infected population.
- `entity_index_fill.nut` created persistent, hidden `prop_dynamic_override` entities in small batches so the allocator could not immediately reuse lower slots.
- The Entity Limits Logger report records `All: 2374` and `Networked: 2159`.
- The direct VScript scan recorded `max=2158`, `over2047=105`, and `maxclass=infected`.

The plugin report is the primary runtime record. The filler and scan scripts are included so the result can be reproduced and cleaned up with `entity_index_fill_cleanup()`.
