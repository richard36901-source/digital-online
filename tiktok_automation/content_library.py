"""
בחירת הסרטון הבא לפרסום מתוך content_bank (round-robin), במבנה מקביל ל-creative_rotation.py
באוטומציית Meta Ads.

מבנה תיקיית content_bank הצפוי:

content_bank/
  videos/           קבצי mp4 (יחסית קצרים, עד 64MB - ראו actions.py)
  captions.json     רשימת כיתובים: [{"caption": "..."}, ...] - מסתובבים באותו סדר round-robin
"""

import json
from pathlib import Path

import config

STATE_FILE = Path("./content_rotation_state.json")


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"video_idx": -1, "caption_idx": -1}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_available_videos() -> list[Path]:
    d = Path(config.CONTENT_BANK_PATH) / "videos"
    if not d.exists():
        return []
    return sorted([p for p in d.iterdir() if p.suffix.lower() in (".mp4", ".mov")])


def get_captions() -> list[dict]:
    captions_file = Path(config.CONTENT_BANK_PATH) / "captions.json"
    if not captions_file.exists():
        return [{"caption": ""}]
    return json.loads(captions_file.read_text(encoding="utf-8"))


def pick_next_video() -> dict | None:
    """
    בוחר את הסרטון + הכיתוב הבאים בתור (round-robin), ומעדכן את קובץ המצב כדי שהפעם
    הבאה תבחר את הבא בתור. מחזיר {"video_path": Path, "caption": str} או None אם התיקייה ריקה.
    """
    videos = get_available_videos()
    captions = get_captions()
    if not videos:
        return None

    state = _load_state()
    next_video_idx = (state.get("video_idx", -1) + 1) % len(videos)
    next_caption_idx = (state.get("caption_idx", -1) + 1) % max(len(captions), 1)
    _save_state({"video_idx": next_video_idx, "caption_idx": next_caption_idx})

    caption = captions[next_caption_idx].get("caption", "") if captions else ""
    return {
        "video_path": videos[next_video_idx],
        "caption": f"{caption}{config.DEFAULT_CAPTION_SUFFIX}",
    }
