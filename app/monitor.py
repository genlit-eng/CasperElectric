import os
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.browser_monitor import BrowserMonitor
from app.state_store import StateStore
from app.telegram import TelegramNotifier


def main() -> None:
    exhibition_no = os.getenv("EXHIBITION_NO", "E20260902")
    state_file = os.getenv("STATE_FILE", "state.json")

    try:
        notifier = TelegramNotifier()
        browser_monitor = BrowserMonitor(exhibition_no=exhibition_no, state_file=state_file)

        # 1. 차량 검색 수행 (기존 기획전 종료 시 최신 기획전 자동 발견 포함)
        new_items = browser_monitor.scan_once()
        active_exhibition_no = browser_monitor.exhibition_no

        # 2. 기획전 번호 기반 상태 관리 (기획전 변경 시 자동 초기화)
        state_store = StateStore(file_path=state_file, exhibition_no=active_exhibition_no)
        seen_ids = state_store.load()

        # 3. 기획전 변경 감지 시 텔레그램 알림 발송
        if state_store.is_exhibition_changed:
            prev = state_store.previous_exhibition_no or "이전"
            change_msg = (
                f"📢 <b>[캐스퍼 일렉트릭 기획전 변경 감지]</b>\n\n"
                f"기획전 번호: <code>{prev}</code> ➡️ <code>{active_exhibition_no}</code>\n"
                f"새로운 기획전이 시작되어 차량 목록을 자동으로 초기화하고 모니터링을 시작합니다."
            )
            try:
                notifier.send_message(change_msg)
                print(f"Sent exhibition change alert to Telegram: {prev} -> {active_exhibition_no}")
            except Exception as exc:
                print(f"Failed to send exhibition change notification: {exc}")

        # 4. 신규 차량 필터링
        filtered = []
        new_ids: List[str] = []
        for item in new_items:
            vehicle_id = str(item.get("id") or item.get("name") or item.get("link") or "").strip()
            if not vehicle_id or vehicle_id in seen_ids:
                continue
            filtered.append(item)
            new_ids.append(vehicle_id)

        if not filtered:
            state_store.save(seen_ids)
            print("새로 등록된 기획전 차량이 없습니다.")
            return

        # 5. 신규 차량 알림 전송
        for car in filtered:
            try:
                message = notifier.build_message(car)
                notifier.send_message(message)
                print(f"Sent alert for {car.get('name', 'unknown')}")
            except Exception as exc:
                print(f"Telegram send failed for {car.get('id')}: {exc}")

        state_store.add(new_ids)
        print(f"Saved {len(new_ids)} new vehicle IDs for exhibition {active_exhibition_no}.")
    except Exception as exc:
        print(f"Unexpected monitor failure: {exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
