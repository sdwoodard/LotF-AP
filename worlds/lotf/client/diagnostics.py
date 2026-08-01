from __future__ import annotations

import logging
import os
import platform
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUPS = 5


def default_data_root() -> Path:
    configured = os.environ.get("LOTF_AP_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "LotFArchipelago"
    state_home = os.environ.get("XDG_STATE_HOME")
    return (Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state") / "LotFArchipelago"


def create_diagnostic_logger(root: Path | None = None) -> tuple[logging.LoggerAdapter, Path, str]:
    """Create the private, append-only support log used by the LotF client.

    The Archipelago client already has its normal console/file logging.  This
    deliberately separate logger records bridge and recovery decisions without
    inheriting chat, server passwords, or other unrelated multiworld traffic.
    """

    data_root = root or default_data_root()
    log_directory = data_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    path = log_directory / "lotf-client.log"
    run_id = uuid.uuid4().hex[:12]

    base = logging.getLogger(f"LotFDiagnostic.{run_id}")
    base.setLevel(logging.DEBUG)
    base.propagate = False
    handler = RotatingFileHandler(
        path,
        mode="a",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUPS,
        encoding="utf-8",
        delay=False,
    )
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03dZ %(levelname)s run=%(run_id)s session=%(session)s room=%(room_fingerprint)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    base.addHandler(handler)
    adapter = logging.LoggerAdapter(
        base,
        {"run_id": run_id, "session": "none", "room_fingerprint": "none"},
    )
    adapter.info(
        "client_start python=%s platform=%s executable=%s",
        platform.python_version(),
        platform.platform(),
        Path(sys.executable).name,
    )
    return adapter, path, run_id


def close_diagnostic_logger(logger: logging.LoggerAdapter) -> None:
    logger.info("client_stop")
    for handler in tuple(logger.logger.handlers):
        handler.flush()
        handler.close()
        logger.logger.removeHandler(handler)
