# Installation and recovery

The supported workflow is a private copy. The source game may live in a Steam library, but the installer never writes to that directory.

## 1. Check the build

The manifest is bound to build `23990068`. Point `--game` at the root containing `left4dead2.exe` on Windows/Proton, or the Linux dedicated server root containing `srcds_run` and `left4dead2/`.

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

The command reads the required files and compares size and full SHA-256. A mismatch stops before copying anything.

Use Steam's **Properties → Installed Files → Browse** to find the source
root, or pass an existing dedicated-server root. Path selection is explicit;
the installer does not search or modify other Steam libraries. On Windows,
use `py -3` instead of `python3`, and PowerShell paths such as
`--game 'D:\SteamLibrary\steamapps\common\Left 4 Dead 2'`.

## 2. Preview and install

Always do a dry run first:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --target "$HOME/L4D2-4096-client" --dry-run
```

Then remove `--dry-run`. If `--target` is omitted, the installer chooses `~/<game>-l4d2-4096` outside the Steam library. An existing target must contain the project marker and requires `--replace`; it is renamed to a timestamped backup before the new copy is swapped into place.

The Linux dedicated-server manifest is installed the same way:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/linux-server.json \
  --game "/path/to/private-server" \
  --target "$HOME/l4d2-4096-server" --dry-run
```

The final target contains `l4d2-4096-install.json`, which records the source, manifest, build, module hashes, and backup path.

## 3. Run matched images

Start the Linux server from its private target. Start the Windows or Proton client from its private target. Do not connect a vanilla client to a patched server or a patched client to a vanilla server when using index `2048` or above.

For a private Linux LAN server (choose an unused test port):

```bash
cd "$HOME/l4d2-4096-server"
./srcds_run -game left4dead2 -insecure -console -port 27132 \
  +sv_lan 1 +map c1m1_hotel
```

Keep Steam logged into the legitimate owner account. A Windows test client
can be started from PowerShell with its private executable:

```powershell
& "$HOME\L4D2-4096-client\left4dead2.exe" -steam -insecure -console
```

Then use the game console: `connect <server-LAN-address>:27132`.
Native Windows runtime acceptance is pending; the tested runtime uses the
same Windows modules through Proton. For that path,
`tools/linux/run_proton_client.py --help` exposes explicit private game,
Proton, prefix and server paths and records module identities. The script's
host-specific defaults must be overridden on another machine.

Windows native dedicated server and Linux native client are not in the tested support set. Do not infer support from a successful file copy.

## Restore or remove

For a replaced marked target, restore the previous copy:

```bash
python3 tools/release/install.py restore \
  --receipt "$HOME/L4D2-4096-client/l4d2-4096-install.json"
```

For a newly created target, the receipt has no backup. Removal requires the explicit safety flag:

```bash
python3 tools/release/install.py restore \
  --receipt "$HOME/L4D2-4096-client/l4d2-4096-install.json" \
  --remove-created
```

If a patch assertion fails, the temporary directory is discarded and an existing target is restored. Backed-up module hashes are verified before restore. The original Steam tree is never an installation target. D66 exercised these operations on a module-only fixture; a fresh full-size user installation remains a separate acceptance step.
