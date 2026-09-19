import os
from typing import Any, Dict

import requests


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            print("Telegram settings missing. Skipping notification.")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        response = requests.post(
            f"{self.base_url}/sendMessage",
            data=payload,
            timeout=30,
        )
        response.raise_for_status()
        return True

    def build_message(self, car: Dict[str, Any]) -> str:
        name = car.get("name", "미상")
        trim = car.get("trim", "미상")
        color = car.get("color", "미상")
        price = car.get("price", 0)
        delivery_center = car.get("deliveryCenter", "미상")
        link = car.get("link", "")

        price_text = f"{int(float(price)):,}원" if isinstance(price, (int, float, str)) and str(price).replace(".", "", 1).isdigit() else str(price)

        message = (
            f"<b>신규 캐스퍼 등록</b>\n"
            f"차량: <b>{name}</b>\n"
            f"트림: {trim}\n"
            f"색상: {color}\n"
            f"가격: {price_text}\n"
            f"출고센터: {delivery_center}\n"
        )

        if link:
            message += f"링크: <a href='{link}'>바로 확인</a>"
        return message
