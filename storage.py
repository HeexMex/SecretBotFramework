"""Персистентное хранилище: задачи, заметки и любые списки по комнатам."""

import json
from pathlib import Path

DATA_DIR = Path("bot_data")


def _room_file(room_id: str, kind: str) -> Path:
    safe_id = room_id.replace(":", "_").replace("!", "")
    d = DATA_DIR / safe_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{kind}.json"


def load_list(room_id: str, kind: str) -> list[dict]:
    f = _room_file(room_id, kind)
    if f.exists():
        return json.loads(f.read_text())
    return []


def save_list(room_id: str, kind: str, data: list[dict]) -> None:
    _room_file(room_id, kind).write_text(json.dumps(data, ensure_ascii=False, indent=2))
