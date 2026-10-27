# Development and reproducible builds

The repository contains patch manifests, source-side generators, runtime probes and reports. It does not contain complete Valve binaries. Work from a verified private copy and keep the Steam library read-only.

## Build inputs

The address tables are tied to build `23990068`. Existing lower-level entry points remain available:

```bash
python3 engine/verify_pe.py
python3 tools/precheck_server.py
python3 tools/build_client.py
python3 tools/build_server.py
python3 tools/build_join_kit.py --game "/path/to/Left 4 Dead 2"
```

The older builders use the environment variables documented in `tools/config.py`. The D66 public installer consumes the generated delta manifests instead of requiring these analysis tools on an end-user machine.

## Release assets

`tools/release/build_manifests.py` creates a manifest from a verified original and candidate tree. It records only sparse old/new byte hunks, sizes and SHA-256 identities. `tools/release/build_assets.py` generates the SVG diagrams and compact benchmark JSON from the D65 evidence contract.

```bash
python3 tools/release/build_assets.py --evidence-root /path/to/runs/d65
python3 -m py_compile tools/release/*.py
```

## SourceMod probe

The tested compatibility sources, gamedata and `.sp` probe live under `tools/sourcemod/`. The pinned builder and complete commands are in [the compatibility recipe](../tools/sourcemod/d65_compatibility.md). Keep the source commits and the exact SDK header delta in sync with `docs/compatibility.md`. Do not broaden the compatibility claim when adding an untested extension.

## Review checklist

Before committing a release-candidate change:

1. Run `git diff --check`.
2. Run Python syntax checks and JSON parsing.
3. Run the D65 evidence checker.
4. Run the installer fixture or a private-copy dry run.
5. Check that no Valve binary, credential, core dump or private raw run was added.
6. Update the release-readiness report if the tested scope changes.
