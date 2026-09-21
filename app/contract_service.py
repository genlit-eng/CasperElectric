import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, async_playwright

class ContractService:
    @staticmethod
    async def configure_estimation(page: Page) -> bool:
        try:
            await page.wait_for_selector(".estimation, .estimate-tool, button:has-text('계약하기')", timeout=10000)
        except Exception:
            pass

        # 1. 추가 보조금 대상 (국고) 체크박스: 다자녀 가구 (2자녀), 기존 내연기관차 교체
        try:
            dajanyeo = page.locator("label:has-text('다자녀 가구 (2자녀)'), .el-checkbox:has-text('다자녀 가구 (2자녀)')")
            if await dajanyeo.count() > 0:
                is_checked = await dajanyeo.first.evaluate("el => el.classList.contains('is-checked')")
                if not is_checked:
                    await dajanyeo.first.click()
                    await page.wait_for_timeout(300)
                    print("[ContractService] 다자녀 가구 (2자녀) 선택 완료")
        except Exception as e:
            print(f"[ContractService] 다자녀 가구 선택 실패: {e}")

        try:
            naeyeon = page.locator("label:has-text('기존 내연기관차 교체'), .el-checkbox:has-text('기존 내연기관차 교체')")
            if await naeyeon.count() > 0:
                is_checked = await naeyeon.first.evaluate("el => el.classList.contains('is-checked')")
                if not is_checked:
                    await naeyeon.first.click()
                    await page.wait_for_timeout(300)
                    print("[ContractService] 기존 내연기관차 교체 선택 완료")
        except Exception as e:
            print(f"[ContractService] 내연기관차 교체 선택 실패: {e}")

        # 1-2. 신청 유형: 개인, 면세구분: 일반
        try:
            gaein = page.locator("label:has-text('개인'), .el-radio:has-text('개인')")
            if await gaein.count() > 0:
                is_chk = await gaein.first.evaluate("el => el.classList.contains('is-checked')")
                if not is_chk:
                    await gaein.first.click()
                    await page.wait_for_timeout(200)

            ilban = page.locator("label:has-text('일반'), .el-radio:has-text('일반')")
            if await ilban.count() > 0:
                is_chk = await ilban.first.evaluate("el => el.classList.contains('is-checked')")
                if not is_chk:
                    await ilban.first.click()
                    await page.wait_for_timeout(200)
        except Exception:
            pass

        # 2. 지역 드롭다운 (배송지역, 전기차 구매보조금 신청 지역, 공채)
        try:
            sido_inputs = page.locator("input[placeholder='시/도 선택']")
            sigun_inputs = page.locator("input[placeholder*='시/군']")
            sido_count = await sido_inputs.count()
            sigun_count = await sigun_inputs.count()

            for i in range(min(sido_count, 3)):
                inp = sido_inputs.nth(i)
                val = await inp.input_value()
                if val != "경북":
                    await inp.click()
                    await page.wait_for_timeout(250)
                    opt = page.locator(".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item").filter(
                        has_text=re.compile(r"^\s*경북\s*$")
                    )
                    if await opt.count() > 0:
                        await opt.first.click()
                        await page.wait_for_timeout(250)

                # Then sigun
                if i < sigun_count:
                    sinp = sigun_inputs.nth(i)
                    sval = await sinp.input_value()
                    if "구미" not in sval:
                        await sinp.click()
                        await page.wait_for_timeout(250)
                        sopt = page.locator(".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item").filter(
                            has_text=re.compile(r"^\s*구미시\s*$")
                        )
                        if await sopt.count() > 0:
                            await sopt.first.click()
                            await page.wait_for_timeout(250)

            print("[ContractService] 배송/보조금/공채 지역(경북 구미시) 설정 완료")
        except Exception as e:
            print(f"[ContractService] 지역 드롭다운 설정 실패: {e}")

        return True

    @classmethod
    async def generate_auto_contract_url(
        cls,
        page: Page,
        car_prod_no: str,
        criterion_ym: str,
        exhb_no: str
    ) -> Optional[str]:
        query = urllib.parse.urlencode({
            "carProductionNumber": car_prod_no,
            "criterionYearMonth": criterion_ym,
            "exhbNo": exhb_no,
        }, quote_via=urllib.parse.quote)
        detail_url = f"https://casper.hyundai.com/vehicles/car-list/detail?{query}"

        try:
            print(f"[ContractService] 견적 생성 시작: {car_prod_no}")
            await page.goto(detail_url, wait_until="networkidle")

            # 견적내기 버튼 찾기 및 클릭
            quote_btn = page.locator("button:has-text('견적내기')").first
            if await quote_btn.count() == 0:
                print(f"[ContractService] 견적내기 버튼 없음: {car_prod_no}")
                return None

            await quote_btn.click()
            await page.wait_for_timeout(1000)

            # 정책 동의 팝업 확인
            dialog = page.locator(".el-dialog:visible")
            if await dialog.count() > 0:
                confirm_btn = dialog.locator("button:has-text('확인했습니다'), button:has-text('확인')").first
                if await confirm_btn.count() > 0:
                    await confirm_btn.click()

            try:
                await page.wait_for_url("**/estimation**", timeout=10000)
            except Exception:
                await page.wait_for_timeout(3000)

            if "estimationUrl=" not in page.url:
                print(f"[ContractService] 견적 URL 진입 실패: {page.url}")
                return None

            est_url = page.url
            print(f"[ContractService] 견적 페이지 진입 성공: {est_url}")

            # 옵션 자동 세팅 (경북 구미시, 다자녀 2자녀, 노후차 교체)
            await cls.configure_estimation(page)
            await page.wait_for_timeout(1000)

            return est_url
        except Exception as e:
            print(f"[ContractService] 견적 URL 생성 중 오류: {e}")
            return None

