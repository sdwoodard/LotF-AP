from worlds.LauncherComponents import Component, Type, components, icon_paths, launch

from .data import GAME


ICON_KEY = "Lords of the Fallen"
icon_paths[ICON_KEY] = "ap:worlds.lotf/assets/lotf-icon.png"


def run_client(*args: str) -> None:
    from .client.launch import launch_client

    launch(launch_client, name="Lords of the Fallen Client", args=args)


components.append(
    Component(
        "Lords of the Fallen Client",
        func=run_client,
        game_name=GAME,
        component_type=Type.CLIENT,
        icon=ICON_KEY,
        supports_uri=True,
    )
)
