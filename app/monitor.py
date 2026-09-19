import os
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.casper_client import CasperClient
from app.state_store import StateStore
from app.telegram import TelegramNotifier


def main() -> None:
    exhibition_no = os.getenv("EXHIBITION_NO", "E20260133")
    state_file = os.getenv("STATE_FILE", "state.json")

    try:
        client = CasperClient(exhibition_no=exhibition_no)
        notifier = TelegramNotifier()
        state_store = StateStore(file_path=state_file)

        raw_cars = client.fetch_cars()
        seen_ids = state_store.load()
        new_items: List[dict] = []
        new_ids: List[str] = []

        for car in raw_cars:
            normalized = client.normalize_car(car)
            vehicle_id = normalized.get("id", "")
            if not vehicle_id or vehicle_id in seen_ids:
                continue
            new_items.append(normalized)
            new_ids.append(vehicle_id)

        if not new_items:
            print("No new cars detected.")
            return

        for car in new_items:
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
