# app/core/storage/memory_store.py

import json
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parent
MEM_FILE = BASE / "memory.json"

def _ensure_memfile():
    MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEM_FILE.exists():
        MEM_FILE.write_text(json.dumps({"sessions": []}, indent=2), encoding="utf-8")

def load_memory() -> Dict[str, Any]:
    _ensure_memfile()
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"sessions": []}

def save_memory(data: Dict[str, Any]):
    _ensure_memfile()
    with open(MEM_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

def add_session(entry: Dict[str, Any]):
    mem = load_memory()
    sessions = mem.get("sessions", [])
    sessions.insert(0, entry)
    mem["sessions"] = sessions[:100]
    save_memory(mem)

def list_sessions() -> List[Dict[str, Any]]:
    mem = load_memory()
    return mem.get("sessions", [])
