# -*- coding: utf-8 -*-
import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, async_playwright

class ContractService:
    @staticmethod
    async def configure_estimation(page: Page) -> bool:
        """
        견적 페이지에서 사용자 지정 조건(경북 구미시, 다자녀 2자녀, 노후차 교체, 일반, 공채 구미시)을 자동 세팅합니다.
        PC(단일 화면) 및 모바일(5단계 위저드) 환경을 모두 지원합니다.
        """
        try:
            await page.wait_for_selector(
                ".estimation, .estimate-tool, button:has-text('계약하기'), button:has-text('다음')",
                timeout=10000
            )
        except Exception:
            pass

        # 모바일 환경(5단계 위저드) 여부 확인
        is_mobile = "m.casper" in page.url or await page.locator("button:has-text('다음')").count() > 0

        if is_mobile:
            print("[ContractService] 모바일 5단계 견적 위저드 자동 설정 시작...")
            try:
                # 헬퍼 함수: 드롭다운 선택
                async def pick_select(ph_text: str, target_val: str) -> bool:
                    try:
                        inputs = page.locator(f"input[placeholder*='{ph_text}']")
                        count = await inputs.count()
                        for i in range(count):
                            inp = inputs.nth(i)
                            if await inp.is_visible():
                                await inp.click()
                                await page.wait_for_timeout(350)
                                opt = page.locator(
                                    ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                                ).filter(has_text=re.compile(rf"^\s*{target_val}\s*$|{target_val}"))
                                if await opt.count() > 0:
                                    await opt.first.scroll_into_view_if_needed()
                                    await opt.first.click()
                                    await page.wait_for_timeout(400)
                                    return True
                    except Exception as e:
                        print(f"[ContractService] 드롭다운({ph_text} -> {target_val}) 선택 실패: {e}")
                    return False

                # --- STEP 1: 배송지역 (경북 구미시) ---
                print("[ContractService] Step 1 배송지역 설정...")
                await pick_select("시/도", "경북")
                await pick_select("시/군", "구미시")
                next_btn = page.locator("button:has-text('다음')").first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                    # 원거리 배송 안내 등 팝업 확인
                    confirm_btn = page.locator("button:has-text('확인'), button:has-text('확인했습니다')").first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        await page.wait_for_timeout(500)

                # --- STEP 2: 포인트 & 할인 ---
                print("[ContractService] Step 2 포인트&할인 통과...")
                next_btn = page.locator("button:has-text('다음')").first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                    confirm_btn = page.locator("button:has-text('확인'), button:has-text('확인했습니다')").first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        await page.wait_for_timeout(500)

                # --- STEP 3: 전기차 구매보조금 (경북 구미시, 다자녀 2자녀, 노후차 교체) ---
                print("[ContractService] Step 3 구매보조금 설정...")
                await pick_select("시/도", "경북")
                await pick_select("시/군", "구미시")

                dajanyeo = page.locator("label:has-text('다자녀 가구 (2자녀)'), .el-checkbox:has-text('다자녀 가구 (2자녀)')")
                if await dajanyeo.count() > 0 and await dajanyeo.first.is_visible():
                    is_chk = await dajanyeo.first.evaluate("el => el.classList.contains('is-checked')")
                    if not is_chk:
                        await dajanyeo.first.click()
                        await page.wait_for_timeout(300)

                naeyeon = page.locator("label:has-text('기존 내연기관차 교체'), .el-checkbox:has-text('기존 내연기관차 교체')")
                if await naeyeon.count() > 0 and await naeyeon.first.is_visible():
                    is_chk = await naeyeon.first.evaluate("el => el.classList.contains('is-checked')")
                    if not is_chk:
                        await naeyeon.first.click()
                        await page.wait_for_timeout(300)

                next_btn = page.locator("button:has-text('다음')").first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                    confirm_btn = page.locator("button:has-text('확인'), button:has-text('확인했습니다')").first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        await page.wait_for_timeout(500)

                # --- STEP 4: 등록비용 (공채: 경북 구미시) ---
                print("[ContractService] Step 4 등록비용 공채 설정...")
                await pick_select("시/도", "경북")
                await pick_select("시/군", "구미시")

                next_btn = page.locator("button:has-text('다음')").first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                    confirm_btn = page.locator("button:has-text('확인'), button:has-text('확인했습니다')").first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        await page.wait_for_timeout(500)

                print("[ContractService] Step 5 견적완료 화면 진입 성공")
                return True
            except Exception as e:
                print(f"[ContractService] 모바일 5단계 위저드 처리 중 오류: {e}")
                return False

        # PC 단일 화면 환경
        print("[ContractService] PC 견적 화면 옵션 자동 설정 시작...")
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

            print("[ContractService] PC 배송/보조금/공채 지역(경북 구미시) 설정 완료")
        except Exception as e:
            print(f"[ContractService] PC 지역 드롭다운 설정 실패: {e}")

        return True

    @classmethod
    async def generate_auto_contract_url(
        cls,
        page: Page,
        car_prod_no: str,
        criterion_ym: str,
        exhb_no: str
    ) -> Optional[str]:
        if not criterion_ym:
            criterion_ym = datetime.now().strftime("%Y%m")
        if not exhb_no:
            exhb_no = "E20260902"

        query = urllib.parse.urlencode({
            "carProductionNumber": car_prod_no,
            "criterionYearMonth": criterion_ym,
            "exhbNo": exhb_no,
        }, quote_via=urllib.parse.quote)
        detail_url = f"https://casper.hyundai.com/vehicles/car-list/detail?{query}"

        try:
            print(f"[ContractService] 견적 생성 시작: {car_prod_no}")
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=25000)

            # 견적내기 버튼 렌더링 대기 및 클릭
            try:
                quote_btn = await page.wait_for_selector(
                    "button:has-text('견적내기'), a:has-text('견적내기')",
                    timeout=15000
                )
                await quote_btn.click()
                await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[ContractService] 견적내기 버튼 찾기 실패: {car_prod_no}, {e}")
                return None

            # 기획전 정책 동의 팝업 확인 (확인했습니다 / 확인)
            try:
                confirm_btn = page.locator("button:has-text('확인했습니다'), button:has-text('확인')").first
                await confirm_btn.click(timeout=4000)
                print("[ContractService] 기획전 정책 안내 팝업 확인 클릭")
                await page.wait_for_timeout(1500)
            except Exception:
                pass

            for _ in range(15):
                if "estimationUrl=" in page.url or "/estimation" in page.url:
                    break
                await page.wait_for_timeout(500)

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
