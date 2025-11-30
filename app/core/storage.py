# app/core/storage.py
"""
Simple file-backed memory_store for sessions.

Usage:
    from core.storage import memory_store
    memory_store.add_session({...})
    memory_store.list_sessions()
    memory_store.clear_sessions()
    memory_store.remove_session(index)
"""

import json
from pathlib import Path
from typing import List, Dict

BASE = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
MEM_FILE = STORAGE_DIR / "memory.json"

def _read() -> List[Dict]:
    if not MEM_FILE.exists():
        return []
    try:
        return json.loads(MEM_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write(arr):
    MEM_FILE.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")

class _MemoryStore:
    def add_session(self, entry: Dict):
        arr = _read()
        arr.insert(0, entry)
        _write(arr)

    def list_sessions(self) -> List[Dict]:
        return _read()

    def clear_sessions(self):
        _write([])

    def remove_session(self, index: int):
        arr = _read()
        if 0 <= index < len(arr):
            arr.pop(index)
            _write(arr)

    def get_session(self, index: int):
        arr = _read()
        if 0 <= index < len(arr):
            return arr[index]
        return None

# singleton instance
memory_store = _MemoryStore()
