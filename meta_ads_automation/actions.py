"""
ביצוע פעולות אמיתיות מול Meta Marketing API: השהיית מודעה, החלפת קריאטיב/קופי.
כל פעולה עוברת קודם דרך config.DRY_RUN - אם True, רק נרשם ללוג ולא מבוצע בפועל.
"""

import requests
import config


def pause_ad(ad_id: str) -> dict:
    """משהה מודעה (status=PAUSED)."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "pause", "ad_id": ad_id}

    url = f"{config.GRAPH_URL}/{ad_id}"
    resp = requests.post(url, data={
        "status": "PAUSED",
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בהשהיית מודעה {ad_id}: {data['error']}")
    return {"dry_run": False, "action": "pause", "ad_id": ad_id, "result": data}


def create_ad_creative(ad_account_id: str, name: str, page_id: str, image_hash: str = None,
                        video_id: str = None, message: str = "", link: str = "",
                        headline: str = "") -> str:
    """
    יוצר אובייקט קריאטיב חדש (adcreative) מתוך תמונה/וידאו + טקסט, ומחזיר creative_id.
    יש להעלות קודם את קובץ המדיה (ראו creative_rotation.upload_image / upload_video).
    """
    if config.DRY_RUN:
        return "DRY_RUN_CREATIVE_ID"

    url = f"{config.GRAPH_URL}/act_{ad_account_id}/adcreatives"

    object_story_spec = {
        "page_id": page_id,
        "link_data": {
            "message": message,
            "link": link,
            "name": headline,
        } if link else {},
    }
    if image_hash:
        object_story_spec["link_data"]["image_hash"] = image_hash
    if video_id:
        object_story_spec["video_data"] = {"video_id": video_id, "message": message}
        object_story_spec.pop("link_data", None)

    payload = {
        "name": name,
        "object_story_spec": str(object_story_spec).replace("'", '"'),
        "access_token": config.ACCESS_TOKEN,
    }
    resp = requests.post(url, data=payload, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל ביצירת קריאטיב עבור act_{ad_account_id}: {data['error']}")
    return data["id"]


def swap_ad_creative(ad_id: str, new_creative_id: str) -> dict:
    """מחליף את הקריאטיב של מודעה קיימת בקריאטיב חדש שכבר נוצר."""
    if config.DRY_RUN:
        return {"dry_run": True, "action": "swap_creative", "ad_id": ad_id, "new_creative_id": new_creative_id}

    url = f"{config.GRAPH_URL}/{ad_id}"
    resp = requests.post(url, data={
        "creative": '{"creative_id":"%s"}' % new_creative_id,
        "access_token": config.ACCESS_TOKEN,
    }, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"נכשל בהחלפת קריאטיב למודעה {ad_id}: {data['error']}")
    return {"dry_run": False, "action": "swap_creative", "ad_id": ad_id, "result": data}
