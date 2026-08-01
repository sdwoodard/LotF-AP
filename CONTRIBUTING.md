# Contributing

Changes are welcome, especially verified mappings from clean saves and current
Steam builds. Do not submit copyrighted game assets, extracted SDK dumps,
decrypted content, saves belonging to another person, or third-party binaries.

Every location mapping should include:

1. the retail game version and executable hash;
2. the exact reflected asset/function name;
3. a reproducible route from a new character;
4. whether the location is missable, ending-specific, or quest-sensitive; and
5. logs showing one check and exactly one replay-safe item grant.

Run `scripts/windows/Test-Repository.ps1` and
`scripts/windows/Build-Release.ps1` before opening
a pull request. APWorld changes must also pass generation tests against the
minimum supported Archipelago version.

For logic or option changes, install the built APWorld into a clean
Archipelago source checkout and run:

```powershell
scripts/windows/Test-GenerationMatrix.ps1 -ArchipelagoPath "<Archipelago checkout>"
```

The default matrix fills and inspects 1,152 solo, LotF-only, and mixed-game
multiworlds. Across their 3,072 LotF slots it covers every combination of all
finite choice/toggle options, all three accessibility modes, and numeric
minimum/default/maximum boundaries. It also walks progression spheres and
independently tests every active route gate with and without its required item.
