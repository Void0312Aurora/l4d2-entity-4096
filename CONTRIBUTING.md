# Contributing to L4D2-4096

Contributions are welcome, including bug reports, reproducible runtime tests, reverse-engineering findings, platform compatibility work, documentation, and patches.

This project modifies **version-specific game binaries**. The current release manifests target L4D2 build `23990068`; results from another build must be reported separately.

## Reporting a problem

Open a [bug report](https://github.com/Void0312Aurora/l4d2-entity-4096/issues/new/choose) and include:

- Client and server OS/runtime (native Windows, Proton, native Linux, dedicated server or listen server), and whether both sides were patched.
- L4D2 build and, when relevant, module hashes or the installer's `check` output.
- Steps to reproduce, expected behavior, actual behavior, and relevant redacted console logs or traces.
- Whether the issue reproduces with the original binaries, if you can safely test that control.

Please distinguish **server-side high-index observations** from **client-side synchronization**. A successful connection or a high server-side Logger count alone does not establish client-side high-index correctness.

## Submitting a pull request

1. Open an issue first for a substantial change; small fixes and documentation updates can go directly to a PR.
2. Fork the repository, make a focused change, and describe its purpose and affected platforms.
3. For binary patches, document the original module identity, modified offsets/bytes, and the reason for each change. Update affected manifests and technical notes.
4. Include tests or reproducible observations. State what was **not** tested; do not mark a static-only change as runtime-verified.
5. Follow the existing review checklist in [docs/development.md](docs/development.md) and update compatibility/release notes when behavior changes.

Useful checks (run what applies to your change):

```bash
git diff --check
python3 -m py_compile tools/release/*.py
python3 tools/release/install.py --help
```

Runtime tests, original game files and D65/D66 private evidence may not be available to every contributor. Explain which checks you could run rather than claiming unperformed checks passed.

## AI-assisted contributions

**AI-assisted work is welcome.** Contributors are responsible for reviewing, understanding, and validating their submissions. Briefly disclose substantial AI assistance in the PR description, including how you checked the generated work. AI-generated explanations and predicted patch sites are not substitutes for binary assertions or runtime evidence.

## Legal and sensitive material

- **Do not commit or attach Valve game binaries, modified game DLL/SO files, game assets, workshop VPKs, or copyrighted third-party code without appropriate rights.**
- Do not upload Steam credentials/tokens, private identifiers, proprietary crash dumps, or unredacted private logs. Keep original game files and raw process snapshots local.
- Preserve notices and comply with the separate licenses of SourceMod, Metamod:Source, SDKs and other third-party dependencies.
- The [MIT license](LICENSE) covers the original project material the maintainers have the right to license; it does **not** grant rights to Valve or third-party materials.

Be respectful and keep technical discussions focused on reproducible observations and reviewable changes.
