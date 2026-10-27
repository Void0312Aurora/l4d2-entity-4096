# Installation and recovery

The supported workflow patches the existing Steam game directory in place.
Only the modules listed by the manifest are changed. Each one receives an
adjacent `*.l4d2-4096.bak` source backup, so the installer never copies the
full game tree or addons.

The installer verifies all source hashes before writing, then patches and
verifies each module. `--dry-run` performs the same source check without
creating backups or changing files.

## 1. Check the build

The manifest is bound to build `23990068`. Point `--game` at the root
containing `left4dead2.exe` on Windows/Proton, or the Linux dedicated server
root containing `srcds_run` and `left4dead2/`.

An explicit `check` is optional because `install` performs the same precheck.
Use it when you only want to inspect the current state:

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

The command compares file sizes, full SHA-256 identities and module
architecture. It reports either the original state or the patched state and
stops on an unknown or mixed state.

Use Steam's **Properties → Installed Files → Browse** to find the game root.
On Windows, use `py -3` or `python` and a PowerShell path such as
`--game 'F:\SteamLibrary\steamapps\common\Left 4 Dead 2'`.

## 2. Preview and install

Preview without writing files:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" --dry-run
```

Then remove `--dry-run` to patch the same game directory:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

Close the game before installing. On Windows, a running game may keep the
DLLs open and prevent replacement. Steam can overwrite modified modules during
a game update, so run `check` and `install` again after an update.

The Linux dedicated-server manifest is installed the same way:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/linux-server.json \
  --game "/path/to/server-root" --dry-run
```

The game directory contains `l4d2-4096-install.json`, which records the
manifest, build, module hashes and backup names.

## 3. Run matched images

Start the Linux server or Windows/Proton client from the normal game
directory. Do not connect a vanilla client to a patched server or a patched
client to a vanilla server when using index `2048` or above.

For a private Linux LAN server (choose an unused test port):

```bash
cd "/path/to/server-root"
./srcds_run -game left4dead2 -insecure -console -port 27132 \
  +sv_lan 1 +map c1m1_hotel
```

Keep Steam logged into the legitimate owner account. A Windows test client
can be started from PowerShell with the normal executable:

```powershell
& "F:\SteamLibrary\steamapps\common\Left 4 Dead 2\left4dead2.exe" -steam -insecure -console
```

Then use the game console: `connect <server-LAN-address>:27132`.
Native Windows runtime acceptance is pending; the tested runtime uses the
same Windows modules through Proton. For that path,
`tools/linux/run_proton_client.py --help` exposes explicit game, Proton,
prefix and server paths and records module identities.

Windows native dedicated server and Linux native client are not in the tested
support set. Do not infer support from a successful file replacement.

## Restore

Restore the original modules from the receipt:

```bash
python3 tools/release/install.py restore \
  --receipt "/path/to/Left 4 Dead 2/l4d2-4096-install.json"
```

Restore verifies the current patched hashes and the `.l4d2-4096.bak` hashes
before replacing the modules. If Steam has updated a module in the meantime,
the hash check stops instead of overwriting it. The backup files are retained
for a later reinstall.

If a patch assertion fails, no module replacement is committed. The verified
backups are retained for recovery. D66 exercised these operations on a
module-only fixture.
