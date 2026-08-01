# Development

## APWorld

For full local testing, clone upstream Archipelago beside this repository and
copy or link `worlds/lotf` into its `worlds` directory. Install Archipelago's
development requirements, then run:

```powershell
python -m unittest discover -s worlds/lotf/test -t . -v
New-Item -ItemType Directory -Force .\Players
Copy-Item "..\LotF-AP\player-options\Lords of the Fallen.yaml" ".\Players\Lampbearer.yaml"
python Generate.py
```

Linux equivalents use `python3`, `mkdir -p`, and `cp`. Repository-level Bash
validation and packaging are:

```bash
bash ./scripts/linux/test-repository.sh
bash ./scripts/linux/build-release.sh
```

Do not renumber existing item or location IDs. Add new rows at the end of the
relevant tuple in `data.py`; published IDs are protocol compatibility.

## Game-side mapping

`scripts/windows/Extract-GameAssets.ps1` and
`scripts/linux/extract-game-assets.sh` accept a
local `retoc` executable and print
the shipped equipment-item asset paths without unpacking game content. The
repository stores paths and names only; never commit extracted `.uasset`,
`.ucas`, `.utoc`, SDK, PDB, or localization files.

Use a disposable offline save and a UE4SS developer build when validating new
hooks. A mapping is accepted only after a clean process restart demonstrates:

- one vanilla interaction produces one `CHECK`;
- reconnect/resync does not repeat an acknowledged check or grant;
- a crash/older-save load restores the measured post-checkpoint deficit for
  both a unique item and a stackable item, without duplicating either; and
- an opt-in suppressed progression pickup is genuinely absent until received.

## Release

Update `VERSION`, `archipelago.json`, Lua `Bridge.version`, client slot-data
version, and `CHANGELOG.md` together. Run repository validation, both platform
packagers, the full generation matrix, and an offline smoke test. Verify
`SHA256SUMS.txt`, then test both a clean install and an upgrade from freshly
extracted Windows and Linux packages. Tag releases exactly as `v<VERSION>`.
