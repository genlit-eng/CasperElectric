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
        state_store = StateStore(file_path=state_file)
        browser_monitor = BrowserMonitor(exhibition_no=exhibition_no, state_file=state_file)

        seen_ids = state_store.load()
        new_items = browser_monitor.scan_once()
        new_ids: List[str] = []

        filtered = []
        for item in new_items:
            vehicle_id = str(item.get("id") or item.get("name") or item.get("link") or "").strip()
            if not vehicle_id or vehicle_id in seen_ids:
                continue
            filtered.append(item)
            new_ids.append(vehicle_id)

        if not filtered:
            state_store.save(seen_ids)
            print("선택하신 조건에 맞는 기획전 차량이 없습니다.")
            return

        for car in filtered:
            try:
                message = notifier.build_message(car)
                notifier.send_message(message)
                print(f"Sent alert for {car.get('name', 'unknown')}")
            except Exception as exc:
                print(f"Telegram send failed for {car.get('id')}: {exc}")

        state_store.add(new_ids)
        print(f"Saved {len(new_ids)} new vehicle IDs.")
    except Exception as exc:
        print(f"Unexpected monitor failure: {exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
