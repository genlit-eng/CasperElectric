import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from app.contract_service import ContractService
from app.telegram import TelegramNotifier


async def run_auto_contract(car_prod_no: str, criterion_ym: str = "202609", exhb_no: str = "E20260902"):
    notifier = TelegramNotifier()
    print(f"🚀 [AutoContract] 시작: 차량 {car_prod_no}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = await context.new_page()
        try:
            est_url = await ContractService.generate_auto_contract_url(
                page,
                car_prod_no=car_prod_no,
                criterion_ym=criterion_ym,
                exhb_no=exhb_no,
            )
            if est_url:
                msg = (
                    f"⚡ <b>[원클릭 자동 계약 준비 완료]</b>\n\n"
                    f"차량: <code>{car_prod_no}</code>\n"
                    f"옵션: 배송지(구미시) / 보조금(구미시) / 다자녀(2자녀) / 노후차교체 / 공채(구미시) 자동 설정 완료\n\n"
                    f"👉 <a href=\"{est_url}\"><b>🔥 [지금 바로 온라인 계약하기]</b></a>\n"
                    f"<i>(링크를 누르고 '온라인 계약하기'를 누른 뒤 로그인하여 계약을 완료하세요!)</i>"
                )
                notifier.send_message(msg)
                print(f"✅ 계약 URL 생성 및 텔레그램 발송 완료: {est_url}")
            else:
                print(f"❌ 계약 URL 생성 실패 (이미 마감/판매 완료된 차량일 수 있음)")
        finally:
            await context.close()
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Casper auto contract runner")
    parser.add_argument("--car-number", required=True, help="Car production number (e.g. '6X  105040')")
    parser.add_argument("--month", default="202609", help="Criterion year month")
    parser.add_argument("--exhibition", default=os.getenv("EXHIBITION_NO", "E20260902"), help="Exhibition number")
    args = parser.parse_args()

    asyncio.run(run_auto_contract(args.car_number, args.month, args.exhibition))


if __name__ == "__main__":
    main()

