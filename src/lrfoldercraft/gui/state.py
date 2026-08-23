"""What the window remembers between sessions.

Setting the same eight options every time is work the tool can do for the
operator. What it must *not* do is silently carry over a decision whose meaning
depends on something that has changed since -- so two things are deliberately
never restored:

* **Per-folder decisions.** They are keyed by catalog folder id. Restoring them
  against a different catalog would apply an answer given about one folder to
  whatever unrelated folder happens to share that number.
* **The catalog backup switch.** Turning the safety net off should be a decision
  taken for the run at hand, not one inherited from a run three weeks ago.

Everything else the window offers is remembered.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..config import config_dir
from ..logging_setup import get_logger

log = get_logger("gui.state")

STATE_FILE = "gui-state.json"

#: Bumped when a stored key changes meaning, so an old file is discarded rather
#: than misread.
STATE_VERSION = 1


def state_path() -> Path:
    return config_dir() / STATE_FILE


def load_state() -> Dict[str, Any]:
    """What was last saved, or an empty mapping.

    A missing, unreadable or outdated file is not an error: the window simply
    opens with its built-in defaults.
    """
    path = state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        log.warning("Ignoring unreadable %s: %s", path, error)
        return {}
    if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
        log.info("Ignoring %s written by another revision", path)
        return {}
    return data


def save_state(state: Dict[str, Any]) -> bool:
    """Store *state*; return whether it was written.

    Failing to remember a preference must never cost the operator anything, so
    an unwritable directory is logged and shrugged off.
    """
    path = state_path()
    payload = dict(state)
    payload["version"] = STATE_VERSION
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as error:
        log.warning("Could not remember the settings in %s: %s", path, error)
        return False
    return True
