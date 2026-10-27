# Troubleshooting

## “unsupported original” or SHA-256 mismatch

The manifest is tied to build `23990068`. Do not force the patch onto a newer or different file. Verify the Steam library path and let Steam finish updates, then run `check` again. The installer stops before modifying a mismatch.

## Existing `.bak` or receipt

The installer reuses a `.l4d2-4096.bak` only when its hash matches the
manifest's original module. A mismatched backup is never overwritten. Keep the
receipt in the game directory; it is the record used by `restore`.

## Patch assertion failed

This means the source bytes changed between validation and replacement, or the
manifest is not for that build. Keep the failure output, do not edit the
binary manually, and use the receipt plus `.l4d2-4096.bak` files for recovery.

## Client connects but high-index objects are missing

Confirm that both sides use the matching manifest and that the client modules
are patched in the normal Steam game directory. A vanilla client can connect
to low-index content but cannot decode the expanded network index. Check the
module hashes in `l4d2-4096-install.json` and run the release gate.

## SourceMod loads but a plugin fails

The compatibility build only covers the core entity API, SDKTools, SDKHooks and the D65 probe. Disable unrelated native extensions, inspect the plugin’s entity-index assumptions, and compare against [compatibility](compatibility.md). Do not interpret a stock SDKHooks crash or an untested extension as a failure of the core entity patch without a matching trace.

If the server uses the patched Linux modules, do not retain the stock
`sdkhooks.ext.2.l4d2.so` or stock SourceMod core. The old SDKHooks build reads
the original entity-listener offset and can crash while SourceMod is loading;
install the matching rebuilt core/SDKTools/SDKHooks package in the private
server copy first. A `Cbuf_AddText: buffer overflow` warning is a separate
configuration-queue issue. When it comes from `l4d2_specialammo.cfg`, keep
the plugin enabled but load its 80 commands through small sequential `exec`
files, preserving the original command order and values. Do not use the
warning as evidence of an entity-limit regression until the unmodified
engine/server control has been compared.

If a workshop mission reports a KeyValues EOF or invalid mode, inspect the
VPK's `missions/*.txt` entry before changing server binaries. The tested
Deathcraft, Zengcheng and Anemoia files had missing closing braces (and
Deathcraft also reused mode key `0`); repair a private VPK copy or disable the
specific addon, retaining the original for rollback.

## Recovery

Use the receipt with `tools/release/install.py restore`. Do not delete the
Steam game tree or the `.l4d2-4096.bak` files as a recovery step. Preserve the
receipt and first failure log for diagnosis.
