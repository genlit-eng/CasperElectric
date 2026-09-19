import json
import os
from typing import List


class StateStore:
    def __init__(self, file_path: str = "state.json"):
        self.file_path = file_path

    def load(self) -> List[str]:
        if not os.path.exists(self.file_path):
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    return [str(item) for item in data]
        except Exception:
            pass

        return []

    def save(self, ids: List[str]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as handle:
            json.dump(ids, handle, ensure_ascii=False, indent=2)

    def add(self, new_ids: List[str]) -> None:
        current = self.load()
        combined = list(dict.fromkeys(current + [str(item) for item in new_ids]))
        self.save(combined)
