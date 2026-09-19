import json
import os
from typing import List

from app.casper_client import CasperClient
from app.state_store import StateStore
from app.telegram import TelegramNotifier


def main() -> None:
    exhibition_no = os.getenv("EXHIBITION_NO", "E20260133")
    state_file = os.getenv("STATE_FILE", "state.json")

    client = CasperClient(exhibition_no=exhibition_no)
    notifier = TelegramNotifier()
    state_store = StateStore(file_path=state_file)

    try:
        raw_cars = client.fetch_cars()
    except Exception as exc:
        print(f"Failed to fetch cars: {exc}")
        return

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


if __name__ == "__main__":
    main()
