"""
לוג שקוף - כל החלטה ופעולה נרשמת לקובץ JSON Lines, גם אם בוצעה אוטומטית ללא אישור.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import config


def log_event(event: dict) -> None:
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    event = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def print_and_log(event: dict) -> None:
    log_event(event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
