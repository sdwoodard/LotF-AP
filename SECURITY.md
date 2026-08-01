# Security and anti-cheat policy

This project is for offline randomizer play. Never load UE4SS or this mod while
Easy Anti-Cheat, public matchmaking, co-op, or invasions are active. The
installer does not alter, remove, or bypass Easy Anti-Cheat and does not bundle
an EAC-disabling tool.

Report vulnerabilities privately to the repository maintainers. Do not include
save files, Archipelago passwords, Steam credentials, or other secrets in logs.
The bridge stores a room/slot fingerprint, seed and player names, numeric
checks, received-item metadata, primary save paths and hashes, inventory counts,
and diagnostic text under `%LOCALAPPDATA%\LotFArchipelago` (or the XDG state
directory on Linux). It does not log the
Archipelago password, server chat, Steam credentials, or game-save contents.
Review optional YAML and multiworld attachments before sharing a diagnostic
bundle.
