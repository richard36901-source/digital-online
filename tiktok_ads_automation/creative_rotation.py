"""
רוטציית קריאטיב: מעלה וידאו חדש לפי תור, ומחזיר video_id מוכן לעדכון מודעה.

מבנה תיקיית creative_bank הצפוי:

creative_bank/
  <שם לקוח>/            תואם למפתחות ב-config.ADVERTISER_ACCOUNTS
    videos/              קבצי mp4
    copy.json            רשימת טקסטים: [{"ad_text": "..."}, ...]
  _common/                בנק משותף - נופל אליו כל לקוח שאין לו בנק ייעודי משלו

הסקריפט שומר קובץ rotation_state.json כדי לזכור איזה קריאטיב שימש אחרון לכל מודעה,
ולעבור לבא בתור בפעם הבאה (round-robin).
"""

import json
from pathlib import Path

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
    return Path(config.CREATIVE_BANK_PATH) / "_common"


def get_available_videos(client_name: str) -> list[Path]:
    d = _client_bank_dir(client_name) / "videos"
    videos = sorted([p for p in d.iterdir() if p.suffix.lower() in (".mp4", ".mov")]) if d.exists() else []
    if videos:
        return videos
    common_d = _common_bank_dir() / "videos"
    if not common_d.exists():
        return []
    return sorted([p for p in common_d.iterdir() if p.suffix.lower() in (".mp4", ".mov")])


def get_copy_variants(client_name: str) -> list[dict]:
    copy_file = _client_bank_dir(client_name) / "copy.json"
    if not copy_file.exists():
        copy_file = _common_bank_dir() / "copy.json"
    if not copy_file.exists():
        return [{"ad_text": ""}]
    return json.loads(copy_file.read_text(encoding="utf-8"))


def pick_next_creative(client_name: str, ad_id: str) -> dict | None:
    """
    בוחר את הווידאו/טקסט הבאים בתור (round-robin) עבור מודעה נתונה, ומעדכן את
    rotation_state.json כדי שהפעם הבאה תבחר את הבא בתור.
    מחזיר {"video_path": Path, "ad_text": str} או None אם אין ספרייה.
    """
    videos = get_available_videos(client_name)
    copies = get_copy_variants(client_name)
    if not videos:
        return None

    state = _load_state()
    idx = state.get(ad_id, {"video_idx": -1})
    next_video_idx = (idx["video_idx"] + 1) % len(videos)
    next_copy_idx = (idx.get("copy_idx", -1) + 1) % max(len(copies), 1)

    state[ad_id] = {"video_idx": next_video_idx, "copy_idx": next_copy_idx}
    _save_state(state)

    copy = copies[next_copy_idx] if copies else {"ad_text": ""}
    return {
        "video_path": videos[next_video_idx],
        "ad_text": copy.get("ad_text", ""),
    }
