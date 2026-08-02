# GitHub repository settings

These values cannot be committed as normal repository metadata. Configure
them in GitHub's web interface after pushing the repository.

## About panel

On the repository home page, select the gear beside **About** and enter:

- **Description:** `Archipelago multiworld randomizer client and UE4SS mod for Lords of the Fallen (2023).`
- **Website:** `https://archipelago.gg/`
- **Topics:** `archipelago`, `archipelagomw`, `multiworld`, `randomizer`,
  `lords-of-the-fallen`, `lords-of-the-fallen-2023`, `lotf`, `soulslike`,
  `ue4ss`, `unreal-engine-5`, `game-modding`, `python`, `lua`, `windows`,
  `linux`, `proton`

Enable **Releases**. After the first release, the repository or release URL is
a better Website value if it has a stable public address; keep Archipelago as
a prominent README link.

GitHub limits topics to 20 and uses them to group related repositories, so use
the exact lowercase, hyphenated forms above. Review GitHub's suggested topics
after the first push and add only suggestions that accurately describe the
project.

## Social preview

Open **Settings > General > Social preview > Edit**, then upload
`.github/assets/social-preview.jpg`.

The file is 1280x640 with a solid background and is below GitHub's 1 MB upload
limit. After saving, shared-link services may retain the failed prior preview
in cache; use their refresh/debug tool or wait for the cache to expire before
judging the replacement.

## Community features

Under **Settings > General > Features**:

- enable **Issues** for reproducible bug reports;
- enable **Discussions** once there is enough traffic to separate questions
  and seed coordination from defects; and
- keep **Wikis** disabled unless documentation actually moves there. The
  versioned `docs/` directory should remain the source of truth.

Pin the first stable release and add a short announcement discussion containing
the supported Steam build, offline/EAC warning, installation link, and known
limitations.

## Releases

Pushing a tag such as `v0.2.1` runs `.github/workflows/release.yml`. Under
**Settings > Actions > General > Workflow permissions**, confirm that the
workflow may write repository contents, or confirm that organization policy
accepts the workflow's explicit `contents: write` permission.

After publication, edit the release and add:

- one screenshot of the client connected to a room;
- one transparent in-game remote-item pickup screenshot;
- the supported Steam build and executable identity;
- the offline/EAC warning near the top; and
- a direct link to the setup and troubleshooting sections in the README.
