import html
import os
from typing import Any, Dict, List

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

    @staticmethod
    def classify_target(car: Dict[str, Any]) -> int:
        """
        차량 트림 및 옵션을 검사하여 3가지 카테고리로 분류:
        1: 조건 100% 일치 (지정 필수 옵션만 정확히 장착, 추가 옵션 없음)
        2: 조건 충족 + 추가 옵션 포함 (지정 필수 옵션을 모두 포함하고, 추가 옵션이 더 있음)
        3: 조건 미충족 (일반 차량)

        [타겟 조건]
        - 조건 1: 트림이 "라운지" 이고 옵션에 "파킹 어시스트" 포함
        - 조건 2: 트림이 "인스퍼레이션" 이고 옵션에 "파킹 어시스트", "컴포트", "익스테리어 디자인" 포함
        """
        trim = str(car.get("trim", "")).replace(" ", "").lower()

        raw_opts = car.get("raw_options")
        if raw_opts is None:
            opts_str = str(car.get("options", ""))
            raw_opts = [o.split("(")[0].strip() for o in opts_str.split(",") if o.strip()]

        norm_opts: List[str] = [
            opt.replace(" ", "").replace("익세테리어", "익스테리어").lower()
            for opt in raw_opts
            if opt
        ]

        def has_parking(opts: List[str]) -> bool:
            return any("파킹" in o and "어시스트" in o for o in opts)

        def has_comfort(opts: List[str]) -> bool:
            return any("컴포트" in o for o in opts)

        def has_exterior(opts: List[str]) -> bool:
            return any("익스테리어" in o for o in opts)

        # 조건 1: 라운지 트림
        if "라운지" in trim:
            if has_parking(norm_opts):
                if len(norm_opts) == 1:
                    return 1
                else:
                    return 2

        # 조건 2: 인스퍼레이션 트림
        if "인스퍼레이션" in trim:
            if has_parking(norm_opts) and has_comfort(norm_opts) and has_exterior(norm_opts):
                if len(norm_opts) == 3:
                    return 1
                else:
                    return 2

        return 3

    def build_message(self, car: Dict[str, Any]) -> str:
        name = html.escape(str(car.get("name", "미상")).strip())
        trim = html.escape(str(car.get("trim", "미상")).strip())
        color = html.escape(str(car.get("color", "미상")).strip())
        price = car.get("price", 0)
        delivery_center = html.escape(str(car.get("deliveryCenter", "미상")).strip())
        options = car.get("options", "")
        options_text = html.escape(str(options).strip()) if options else "없음 (기본 사양)"
        link = str(car.get("link", "")).strip() or "https://casper.hyundai.com"

        price_text = f"{int(float(price)):,}원" if isinstance(price, (int, float, str)) and str(price).replace(".", "", 1).isdigit() else str(price)

        category = self.classify_target(car)

        contract_url = str(car.get("contract_url") or "").strip()

        contract_target = contract_url if contract_url else link

        if category == 1:
            # 1순위: 지정 조건 100% 일치 (원하는 옵션만 정확히 장착)
            links_block = (
                f"⚡ <a href=\"{contract_target}\"><b>🔥 [⚡ 원클릭 자동 견적/계약 바로가기]</b></a>\n"
                f"<i>(배송지·보조금·공채: 구미시 / 다자녀 2자녀 / 노후차 교체)</i>\n\n"
                f"🔗 <a href=\"{link}\"><b>[차량 상세 정보 확인하기]</b></a>\n"
                f"💡 <i>(한정 재고 특성상 타인이 먼저 계약/선점한 경우 상세 페이지가 마감되어 메인 화면으로 이동될 수 있습니다)</i>"
            )

            msg = (
                f"🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨\n"
                f"🔴 <b>[특급 매칭] 100% 완벽 일치 차량!</b> 🔴\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"<blockquote>🎯 <b>원하시는 조건과 정확히 일치합니다! (추가옵션 없음)</b>\n\n"
                f"🚗 <b>차량:</b> {name}\n"
                f"🏷️ <b>트림:</b> <b>{trim}</b>\n"
                f"🎨 <b>색상:</b> {color}\n"
                f"💰 <b>가격:</b> <b>{price_text}</b>\n"
                f"🏢 <b>출고센터:</b> {delivery_center}\n"
                f"✨ <b>선택옵션:</b> <b>{options_text}</b>\n"
                f"</blockquote>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{links_block}"
            )
        elif category == 2:
            # 2순위: 조건 충족 + 추가 옵션 포함
            links_block = (
                f"⚡ <a href=\"{contract_target}\"><b>🔥 [⚡ 원클릭 자동 견적/계약 바로가기]</b></a>\n"
                f"<i>(배송지·보조금·공채: 구미시 / 다자녀 2자녀 / 노후차 교체)</i>\n\n"
                f"🔗 <a href=\"{link}\"><b>[차량 상세 정보 확인하기]</b></a>\n"
                f"💡 <i>(한정 재고 특성상 타인이 먼저 계약/선점한 경우 상세 페이지가 마감되어 메인 화면으로 이동될 수 있습니다)</i>"
            )

            msg = (
                f"⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐\n"
                f"🟡 <b>[조건 충족] 관심 차량 (추가옵션 포함)</b> 🟡\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"<blockquote>✨ <b>필수 조건을 모두 만족하며, 추가 옵션이 있습니다.</b>\n\n"
                f"🚗 <b>차량:</b> {name}\n"
                f"🏷️ <b>트림:</b> <b>{trim}</b>\n"
                f"🎨 <b>색상:</b> {color}\n"
                f"💰 <b>가격:</b> <b>{price_text}</b>\n"
                f"🏢 <b>출고센터:</b> {delivery_center}\n"
                f"✨ <b>선택옵션:</b> {options_text}\n"
                f"</blockquote>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{links_block}"
            )
        else:
            # 3순위: 조건 미충족 일반 차량 (크로스, 프리미엄 등 모든 신규 등록 차량)
            links_block = (
                f"⚡ <a href=\"{contract_target}\"><b>🔥 [⚡ 원클릭 자동 견적/계약 바로가기]</b></a>\n\n"
                f"🔗 <a href=\"{link}\"><b>[차량 상세 정보 확인하기]</b></a>\n"
                f"💡 <i>(한정 재고 특성상 타인이 먼저 계약/선점한 경우 상세 페이지가 마감되어 메인 화면으로 이동될 수 있습니다)</i>"
            )

            msg = (
                f"📋 <b>[신규 등록] 캐스퍼 신규 차량</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"<blockquote>🚗 <b>차량:</b> {name}\n"
                f"🏷️ <b>트림:</b> <b>{trim}</b>\n"
                f"🎨 <b>색상:</b> {color}\n"
                f"💰 <b>가격:</b> <b>{price_text}</b>\n"
                f"🏢 <b>출고센터:</b> {delivery_center}\n"
                f"✨ <b>선택옵션:</b> {options_text}\n"
                f"</blockquote>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{links_block}"
            )

        return msg
