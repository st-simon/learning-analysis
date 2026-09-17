from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from browser_capture import DEFAULT_EXTENSION_ID, DEFAULT_TOKEN_FILE
from browser_capture_server import load_or_create_token


DEFAULT_CONFIG_FILE = PROJECT_ROOT / "spike" / "browser-source-extension" / "install_config.js"


def configure_extension(
    token_file: Path = DEFAULT_TOKEN_FILE,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> Path:
    token = load_or_create_token(token_file)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    content = f"globalThis.GATE1A_INSTALL_TOKEN = {json.dumps(token)};\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".install-config-", dir=config_file.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, config_file)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return config_file


if __name__ == "__main__":
    configured = configure_extension()
    print(f"configured Gate 1A extension {DEFAULT_EXTENSION_ID} at {configured}")
