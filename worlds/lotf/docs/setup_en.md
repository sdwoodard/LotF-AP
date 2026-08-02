# Lords of the Fallen setup guide

## Before playing

Install Archipelago 0.6.7 or newer and the basic
[RE-UE4SS 3.0.1 package](https://github.com/UE4SS-RE/RE-UE4SS/releases/download/v3.0.1/UE4SS_v3.0.1.zip).
RE-UE4SS is the separate Unreal mod loader used by the game bridge. Keep the game offline and
disable Easy Anti-Cheat for every modded session. Never enter matchmaking,
co-op, or invasions while the mod is installed.

Back up the save directory and use a new character for each seed:

- Windows: `%LOCALAPPDATA%\LOTF2\Saved\SaveGames`
- Proton: `steamapps/compatdata/1501750/pfx/drive_c/users/steamuser/AppData/Local/LOTF2/Saved/SaveGames`

## Windows installation

1. In Steam, right-click the game and choose **Manage > Browse local files**.
   The folder Steam opens, containing `LOTF2.exe`, is the game folder.
2. Extract the *contents* of `UE4SS_v3.0.1.zip` directly into the game's
   `LOTF2\Binaries\Win64` folder. `dwmapi.dll`, `UE4SS.dll`, and `Mods` must be
   directly inside `Win64`, not inside another nested folder.
3. Download the release's `LotF-Archipelago-x.y.z-win64.zip`, choose
   **Extract All**, and double-click `Install-LotFArchipelago.cmd` in the
   extracted folder. In the installer window, select the downloaded ZIP and
   the game folder, then choose **Install**.
4. In Archipelago Launcher, choose **Install APWorld** and select the
   `lotf.apworld` beside the installer.
5. Edit `Lords of the Fallen.yaml`, place it in Archipelago's `Players`
   directory, and generate locally.
6. Leave Steam running on an account that owns the full game. Open **Lords of
   the Fallen Client**, connect to the room, then double-click
   `Start-LotF-AP.cmd`. The saved installation path is used automatically.

The launcher supplies full-game Steam AppID `1501750`, disables the anti-cheat
and EOS paths, and the bridge disables the game's online-mode setting. Confirm
offline status at the main menu before loading the seed. If Friend's Pass is
shown, close the game, verify full-game ownership/files in Steam, start the
unmodded game once, and retry. Do not create `steam_appid.txt`.

## Linux/Proton installation

The Archipelago Linux AppImage cannot currently install custom APWorlds. Use an
Archipelago 0.6.7+ source checkout, extract the release's `-linux.zip`, then
run:

```bash
bash ./install-apworld.sh --archipelago-path "$HOME/src/Archipelago"
bash ./install-lotf-archipelago.sh --game-path "<Steam game folder>"
```

Start `python3 Launcher.py` from the Archipelago checkout, open the game client,
connect, then run:

```bash
bash ./start-lotf-ap.sh
```

Pass `--proton` and `--compat-data` if Steam/Proton auto-detection is wrong.
The native client and Proton bridge share
`${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago`. Override it with
`LOTF_AP_DATA_DIR`; use `LOTF_AP_SAVE_DIR` for a nonstandard save prefix.

## Playing

Start the client and connect it to the correct room and slot before starting
the game. Starting the client first is always safe because it waits for the
file bridge. Starting the game first is safe only while you remain at the title
screen or main menu; do not load the character or collect anything until the
client reports `Game bridge connected` and save synchronization has completed.

If the client closes while the game is open, pause play and reconnect it to the
same room and slot. The mod durably records observed checks and replays any that
the server has not acknowledged. Wait for bridge and save synchronization
before continuing, and run `/resync` if the client requests it.

Run `/bridge` to see the
package and pickup-safety status. Run `/logic` (or `/inlogic`) for a
region-prefixed list of unchecked locations currently reachable with received
items. Results are paged; use `/logic 2` for page two or an area prefix such as
`/logic AR` to filter. The description states where the check is, not what its
randomized item does.

Soulflay boss remembrance stigmas to report boss checks. `any_ending` completes
after any credits sequence. `all_bosses` uses only the audited encounters that
remain available regardless of ending route and quest choices.

## Recovery and troubleshooting

After a crash or older-save load, keep the client connected and let the game
finish loading. The client fingerprints the active `SaveNN.sav`, audits the
actual inventory, and restores only items received after that save's recorded
cursor which are now missing. It never blindly retries an unverified mutation.

If automatic save selection is ambiguous, run `/save_slot <0-99>`, then
`/resync`. Never use one character with two different seeds; cross-room save
bindings intentionally block recovery.

Run `/diagnostics` and create a bundle with
`New-LotFDiagnosticBundle.cmd` (Windows) or
`new-lotf-diagnostic-bundle.sh` (Linux). Include a problem description,
approximate time, generated multiworld, and player YAML when safe. The bundle
does not include saves or server passwords.

If the game updates, compare the executable identity with `docs/GAME_BUILD.md`
and rerun repository/retoc validation before using experimental key or quest
pickup suppression.
