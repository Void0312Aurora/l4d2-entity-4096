# Demo storyboard

No D66 video is claimed in the repository. The host uses GNOME/Wayland. An
actual FFmpeg capture of the Xwayland root display returned a black frame;
it did not capture the game surface. No usable Wayland portal/recorder
source was available to this task. The deliverables are this storyboard,
the guarded capture script and real-log-derived SVG previews.

## 60–90 second sequence

1. Show the private client launch and the matching server build hash.
2. Enter `c1m1_hotel`; show the debug HUD or SourceMod probe reading actual live entity state.
3. Create the 512 high-index props and show the observed range beginning at `2048`.
4. Show one state update and the client observation tick.
5. Show the normal allocator reaching `4095`, then deletion and reuse with the serial increment.
6. Spawn the six special infected while the high-index props remain alive; show damage/death events.
7. Change to `c1m2_streets`, wait for the client to become active, and show the 16 high-index props recreated after the transition.

## Capture prerequisites

- A private Windows/Proton client and matching Linux server.
- A single Steam account with the client already authenticated.
- The D65 scripts and Frida observer available in the private test root.
- A display recorder such as `wf-recorder`, OBS, or a configured FFmpeg `x11grab`/PipeWire source.

Run `tools/release/capture_demo.sh --help` for the guarded command template. It refuses to record without an explicit display source and never starts or stops the game on its own.

Each published clip should include the session ID, module hashes, and the corresponding D65/D66 evidence path in its caption. Do not add raw multi-gigabyte recordings to Git history; publish a short derivative preview separately if a release is approved.
