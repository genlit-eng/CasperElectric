import json
import os
from datetime import datetime
from typing import List, Optional


class StateStore:
    def __init__(self, file_path: str = "state.json", exhibition_no: str = "") -> None:
        self.file_path = file_path
        self.exhibition_no = (exhibition_no or "").strip()
        self.is_exhibition_changed = False
        self.previous_exhibition_no: Optional[str] = None

    def load(self) -> List[str]:
        if not os.path.exists(self.file_path):
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

                # Format 1: Modern dictionary format with exhibition tracking
                if isinstance(data, dict):
                    saved_exhb = str(data.get("exhibition_no", "")).strip()
                    self.previous_exhibition_no = saved_exhb or None
                    if self.exhibition_no and saved_exhb and saved_exhb != self.exhibition_no:
                        self.is_exhibition_changed = True
                        print(
                            f"[기획전 변경 감지] 기획전이 '{saved_exhb}'에서 '{self.exhibition_no}'(으)로 "
                            f"변경되어 기존 차량 상태 목록을 자동으로 초기화합니다."
                        )
                        return []
                    return [str(item) for item in data.get("seen_ids", [])]

                # Format 2: Legacy list format
                if isinstance(data, list):
                    # Default legacy exhibition is September 2026 (E20260902)
                    legacy_default = "E20260902"
                    self.previous_exhibition_no = legacy_default
                    if self.exhibition_no and self.exhibition_no != legacy_default:
                        self.is_exhibition_changed = True
                        print(
                            f"[기획전 변경 감지] 새로운 기획전({self.exhibition_no})이 설정되어 "
                            f"이전 기획전({legacy_default}) 차량 상태를 자동으로 초기화합니다."
                        )
                        return []
                    return [str(item) for item in data]
        except Exception as exc:
            print(f"상태 파일 로드 중 오류 발생: {exc}")

        return []

    def save(self, ids: List[str]) -> None:
        payload = {
            "exhibition_no": self.exhibition_no or "E20260902",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "seen_ids": list(dict.fromkeys(str(item) for item in ids)),
        }
        with open(self.file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def add(self, new_ids: List[str]) -> None:
        current = self.load()
        combined = list(dict.fromkeys(current + [str(item) for item in new_ids]))
        self.save(combined)

    @staticmethod
    def merge_with_remote(file_path: str = "state.json", git_ref: str = "origin/main:state.json") -> bool:
        import subprocess
        remote_data = {}
        try:
            res = subprocess.check_output(["git", "show", git_ref], text=True, stderr=subprocess.DEVNULL)
            remote_data = json.loads(res)
        except Exception:
            pass

        local_data = {}
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
        except Exception:
            pass

        exhb = local_data.get("exhibition_no") or remote_data.get("exhibition_no") or "E20260902"
        local_ids = local_data.get("seen_ids", []) if isinstance(local_data.get("seen_ids"), list) else []
        remote_ids = remote_data.get("seen_ids", []) if isinstance(remote_data.get("seen_ids"), list) else []
        merged_ids = list(dict.fromkeys(remote_ids + local_ids))

        t_local = local_data.get("last_updated", "")
        t_remote = remote_data.get("last_updated", "")
        last_t = max(t_local, t_remote) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        merged = {
            "exhibition_no": exhb,
            "last_updated": last_t,
            "seen_ids": merged_ids
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        return True
