"""
רוטציית קריאטיב: מעלה תמונה/וידאו חדשים לפי תור, ומחזיר creative_id מוכן להחלפה.

מבנה תיקיית creative_bank הצפוי:

creative_bank/
  <שם לקוח>/            למשל: רחל, טל, גל  (תואם למפתחות ב-config.AD_ACCOUNTS)
    images/              קבצי jpg/png
    videos/              קבצי mp4 (אופציונלי)
    copy.json            רשימת טקסטים: [{"message": "...", "headline": "...", "link": "..."}, ...]

הסקריפט שומר קובץ rotation_state.json כדי לזכור איזה קריאטיב שימש אחרון לכל מודעה,
ולעבור לבא בתור בפעם הבאה (round-robin) - כדי לא לחזור על אותו קריאטיב שוב ושוב.
"""

import json
import os
from pathlib import Path

import requests

import config

STATE_FILE = Path("./rotation_state.json")


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _client_bank_dir(client_name: str) -> Path:
  return Path(config.CREATIVE_BANK_PATH) / client_name

def _common_bank_dir() -> Path:
  """בנק קריאטיבים משותף - נופל אליו כל לקוח שאין לו עדיין בנק ייעודי משלו."""
  return Path(config.CREATIVE_BANK_PATH) / "_common"

def get_available_images(client_name: str) -> list[Path]:
  d = _client_bank_dir(client_name) / "images"
  images = sorted([p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]) if d.exists() else []
  if images:
    return images
  common_d = _common_bank_dir() / "images"
  if not common_d.exists():
    return []
  return sorted([p for p in common_d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])

def get_copy_variants(client_name: str) -> list[dict]:
  copy_file = _client_bank_dir(client_name) / "copy.json"
  if not copy_file.exists():
    copy_file = _common_bank_dir() / "copy.json"
  if not copy_file.exists():
    return [{"message": "", "headline": "", "link": ""}]
  return json.loads(copy_file.read_text(encoding="utf-8"))


def pick_next_creative(client_name: str, ad_id: str) -> dict | None:
    """
    בוחר את התמונה/טקסט הבאים בתור (round-robin) עבור מודעה נתונה,
    ומעדכן את rotation_state.json כדי שהפעם הבאה תבחר את הבא בתור.
    מחזיר {"image_path": Path, "message": str, "headline": str, "link": str} או None אם אין ספרייה.
    """
    images = get_available_images(client_name)
    copies = get_copy_variants(client_name)
    if not images:
        return None

    state = _load_state()
    idx = state.get(ad_id, {"image_idx": -1})
    next_image_idx = (idx["image_idx"] + 1) % len(images)
    next_copy_idx = (idx.get("copy_idx", -1) + 1) % max(len(copies), 1)

    state[ad_id] = {"image_idx": next_image_idx, "copy_idx": next_copy_idx}
    _save_state(state)

    copy = copies[next_copy_idx] if copies else {"message": "", "headline": "", "link": ""}
    return {
        "image_path": images[next_image_idx],
        "message": copy.get("message", ""),
        "headline": copy.get("headline", ""),
        "link": copy.get("link", ""),
    }


def upload_image(ad_account_id: str, image_path: Path) -> str:
    """מעלה תמונה לספריית המדיה של חשבון המודעות, מחזיר image_hash."""
    if config.DRY_RUN:
        return f"DRY_RUN_HASH_{image_path.name}"

    url = f"{config.GRAPH_URL}/act_{ad_account_id}/adimages"
    with open(image_path, "rb") as f:
        files = {image_path.name: f}
        resp = requests.post(url, files=files, data={"access_token": config.ACCESS_TOKEN}, timeout=60)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בהעלאת תמונה {image_path}: {data['error']}")
    images = data.get("images", {})
    first_key = next(iter(images))
    return images[first_key]["hash"]
