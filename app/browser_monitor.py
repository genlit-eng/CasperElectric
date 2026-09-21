import asyncio
import hashlib
import json
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    async_playwright = None


BASE_URL = "https://casper.hyundai.com/vehicles/car-list/promotion"
DEFAULT_EXHIBITION_NO = os.getenv("EXHIBITION_NO", "E20260902")
SIDO_ORDER = [
    "서울",
    "경기",
    "인천",
    "강원",
    "대전",
    "세종",
    "충남",
    "충북",
    "대구",
    "경북",
    "부산",
    "울산",
    "경남",
    "광주",
    "전북",
    "전남",
    "제주",
]

# 전기차 구매보조금 신청 지역 고정 설정 (경북 구미시)
SUBSIDY_SIDO = os.getenv("SUBSIDY_SIDO", "경북")
SUBSIDY_SIGUN = os.getenv("SUBSIDY_SIGUN", "구미시")


class BrowserMonitor:
    def __init__(self, exhibition_no: str = DEFAULT_EXHIBITION_NO, state_file: str = "state.json") -> None:
        self.exhibition_no = (exhibition_no or DEFAULT_EXHIBITION_NO).strip()
        self.state_file = state_file
        self._all_captured_api_items: List[Dict[str, Any]] = []
        self._network_candidates: List[str] = []

    @staticmethod
    def _verbose() -> bool:
        return os.getenv("DEBUG_VERBOSE", "false").strip().lower() in {"1", "true", "yes"}

    def load_seen(self) -> set[str]:
        path = Path(self.state_file)
        if not path.exists():
            return set()
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    saved_exhb = str(data.get("exhibition_no", "")).strip()
                    if self.exhibition_no and saved_exhb and saved_exhb != self.exhibition_no:
                        return set()
                    return {str(item) for item in data.get("seen_ids", [])}
                if isinstance(data, list):
                    if self.exhibition_no and self.exhibition_no != "E20260902":
                        return set()
                    return {str(item) for item in data}
        except Exception:
            pass
        return set()

    def save_seen(self, ids: Sequence[str]) -> None:
        path = Path(self.state_file)
        payload = {
            "exhibition_no": self.exhibition_no or "E20260902",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "seen_ids": list(dict.fromkeys(str(item) for item in ids)),
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _dedupe_key(text: str, link: str = "") -> str:
        raw = f"{text}|{link}".strip("|")
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    async def _all_inner_texts(locator) -> List[str]:
        try:
            items = await locator.all_inner_texts()
            return [str(item).strip() for item in items if str(item).strip()]
        except Exception:
            return []

    @staticmethod
    def _clean_option_label(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    async def _open_page(self, page):
        url = f"{BASE_URL}?exhbNo={self.exhibition_no}"
        print(f"페이지 접속: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 기획전이 종료되어 캐스퍼 메인 등으로 리다이렉트되었거나 잘못된 경우
        if "promotion" not in page.url or "exhbNo=" not in page.url:
            print(f"기존 기획전({self.exhibition_no}) 종료 또는 리다이렉트 감지. 메인 페이지에서 최신 기획전 링크 탐색 중...")
            try:
                if page.url.rstrip("/") != "https://casper.hyundai.com":
                    await page.goto("https://casper.hyundai.com", wait_until="domcontentloaded")
                    await page.wait_for_timeout(1500)

                links = await page.locator("a[href*='promotion?exhbNo=E']").all()
                for l in links:
                    href = (await l.get_attribute("href")) or ""
                    match = re.search(r"exhbNo=(E[A-Za-z0-9]+)", href)
                    if match:
                        new_exhb = match.group(1)
                        print(f"[최신 기획전 자동 발견] {new_exhb}")
                        self.exhibition_no = new_exhb
                        url = f"{BASE_URL}?exhbNo={self.exhibition_no}"
                        print(f"새 기획전 페이지 접속: {url}")
                        await page.goto(url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)
                        break
            except Exception as exc:
                print(f"최신 기획전 자동 탐색 중 오류: {exc}")

    async def _capture_vehicle_response(self, response) -> None:
        url_lower = response.url.lower()
        if any(term in url_lower for term in ("/gw/", "api", "product", "vehicle", "car")):
            if response.url not in self._network_candidates:
                self._network_candidates.append(response.url)
        try:
            payload = await response.json()
        except Exception:
            return

        if "/exhibition/cars" in url_lower:
            if self._verbose():
                print(f"차량 페이지 응답: status={response.status} url={response.url}")
                if isinstance(payload, dict) and payload.get("rspStatus"):
                    print(f"차량 페이지 rspStatus: {payload.get('rspStatus')}")

            items = self._find_vehicle_items(payload)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        cid = (
                            item.get("carProductionNumber")
                            or item.get("saleCtyNo")
                            or item.get("vinNo")
                            or item.get("id")
                        )
                        already_exists = False
                        if cid:
                            already_exists = any(
                                (
                                    c.get("carProductionNumber")
                                    or c.get("saleCtyNo")
                                    or c.get("vinNo")
                                    or c.get("id")
                                )
                                == cid
                                for c in self._all_captured_api_items
                            )
                        if not already_exists:
                            self._all_captured_api_items.append(item)

    async def _print_network_candidates(self) -> None:
        if not self._verbose():
            return
        candidates = [
            url for url in self._network_candidates
            if "/exhibition/cars" in url or "/exhibition/filter/" in url
        ]
        if candidates:
            print("페이지 네트워크 후보 URL:")
            for url in candidates[:10]:
                print(f"  {url}")

    @classmethod
    def _find_vehicle_items(cls, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                vehicle_keys = {"carCode", "carName", "modelName", "productCode", "carId", "carProductionNumber"}
                if any(vehicle_keys.intersection(item.keys()) for item in value):
                    return value
            for item in value:
                found = cls._find_vehicle_items(item)
                if found:
                    return found
        elif isinstance(value, dict):
            if isinstance(value.get("discountsearchcars"), list):
                return value["discountsearchcars"]
            for item in value.values():
                found = cls._find_vehicle_items(item)
                if found:
                    return found
        return []

    def _normalize_api_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        vehicle_id = (
            str(item.get("carProductionNumber") or "").strip()
            or str(item.get("saleCtyNo") or "").strip()
            or str(item.get("vinNo") or "").strip()
            or str(item.get("id") or item.get("carId") or item.get("productCode") or "").strip()
        )
        if not vehicle_id:
            vehicle_id = hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]

        car_name = str(item.get("carName") or "캐스퍼 일렉트릭").strip()
        model_name = str(item.get("splitSaleModelName2") or item.get("modelName") or item.get("saleModelName") or "").strip()
        if model_name and model_name not in car_name:
            full_name = f"{car_name} {model_name}"
        else:
            full_name = car_name

        trim = str(item.get("carTrimName") or item.get("trimName") or item.get("trim") or "미상").strip()

        ext_color = str(item.get("exteriorColorName") or item.get("colorName") or "미상").strip()
        int_color = str(item.get("realityInteriorColorName") or item.get("interiorColorName") or "").strip()
        color = f"{ext_color} (내장: {int_color})" if int_color else ext_color

        raw_price = item.get("finalAmount") or item.get("saleCtyPce") or item.get("carPrice") or item.get("salePrice") or item.get("price") or 0
        try:
            price = int(float(str(raw_price).replace(",", "")))
        except (ValueError, TypeError):
            price = 0

        delivery_center = str(item.get("deliveryCenterName") or item.get("deliveryCenter") or "미상").strip()

        # 세부 옵션 추출 (매칭용 raw_options 및 표시용 options)
        choice_options_display = []
        raw_options = []
        for opt in item.get("carChoiceOption") or []:
            if isinstance(opt, dict) and opt.get("choiceOptionName"):
                opt_name = str(opt.get("choiceOptionName")).strip()
                if opt_name:
                    raw_options.append(opt_name)
                    opt_price = opt.get("choiceOptionPrice")
                    if opt_price and str(opt_price).isdigit() and int(opt_price) > 0:
                        pval = int(opt_price)
                        pstr = f"{pval//10000}만원" if pval >= 10000 else f"{pval:,}원"
                        choice_options_display.append(f"{opt_name}({pstr})")
                    else:
                        choice_options_display.append(opt_name)

        if not raw_options and item.get("optionSummary"):
            for o in str(item.get("optionSummary")).split(","):
                clean_o = o.strip()
                if clean_o:
                    raw_options.append(clean_o)
                    choice_options_display.append(clean_o)

        options_text = ", ".join(choice_options_display) if choice_options_display else ""

        # 차량 개별 상세 및 즉시 구매 페이지 다이렉트 URL 생성
        car_prod_no = str(item.get("carProductionNumber") or "").strip()
        criterion_ym = str(item.get("criterionYearMonth") or datetime.now().strftime("%Y%m")).strip()
        exhb_no = str(item.get("exhbNo") or self.exhibition_no).strip()

        if car_prod_no:
            query = urllib.parse.urlencode({
                "carProductionNumber": car_prod_no,
                "criterionYearMonth": criterion_ym,
                "exhbNo": exhb_no,
            }, quote_via=urllib.parse.quote)
            link = f"https://casper.hyundai.com/vehicles/car-list/detail?{query}"
        else:
            link = str(item.get("detailUrl") or f"{BASE_URL}?exhbNo={self.exhibition_no}").strip()

        return {
            "id": vehicle_id,
            "name": full_name,
            "trim": trim,
            "color": color,
            "price": price,
            "deliveryCenter": delivery_center,
            "options": options_text,
            "raw_options": raw_options,
            "link": link,
        }

    async def _find_selects(self, page) -> List[Tuple[Any, List[str]]]:
        selects = page.locator("select")
        count = await selects.count()
        entries: List[Tuple[Any, List[str]]] = []
        for idx in range(count):
            item = selects.nth(idx)
            texts = await self._all_inner_texts(item)
            labels = [self._clean_option_label(text) for text in texts if self._clean_option_label(text)]
            if len(labels) > 1:
                entries.append((item, labels))
        return entries

    async def _get_select_options(self, select_locator) -> List[Dict[str, str]]:
        options = select_locator.locator("option")
        result: List[Dict[str, str]] = []
        count = await options.count()
        for idx in range(count):
            option = options.nth(idx)
            label = self._clean_option_label(await option.inner_text())
            value = (await option.get_attribute("value")) or label
            if not label:
                continue
            result.append({"label": label, "value": value})
        return result

    async def _get_sigun_options(self, sigungu_select) -> List[Dict[str, str]]:
        if sigungu_select is None:
            return []
        options = await self._get_select_options(sigungu_select)
        return [
            item for item in options
            if item["label"] not in {"시/군/구 선택", "선택", "전체", ""}
        ]

    async def _click_search(self, page) -> None:
        selectors = [
            "button:has-text('조회')",
            "button:has-text('검색')",
            "button:has-text('검색하기')",
            "input[type='submit']",
            "a:has-text('조회')",
            "a:has-text('검색')",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            if await locator.count() > 0:
                try:
                    await locator.first.click()
                    await page.wait_for_timeout(1200)
                    return
                except Exception:
                    continue

    async def _extract_result_cards(self, page) -> List[Dict[str, Any]]:
        selectors = [
            ".car-item",
            ".product-item",
            ".vehicle-item",
            "[data-car-code]",
            "li[data-v-a293210e]",
        ]

        collected: List[Dict[str, Any]] = []
        for selector in selectors:
            locators = page.locator(selector)
            count = await locators.count()
            if count == 0:
                continue
            for idx in range(min(count, 50)):
                card = locators.nth(idx)
                text = self._clean_option_label(await card.inner_text())
                if len(text) < 5 or text in {"카드형", "리스트형"}:
                    continue
                href = None
                if await card.locator("a").count() > 0:
                    href = await card.locator("a").first.get_attribute("href")
                item = {
                    "text": text,
                    "href": href or f"{BASE_URL}?exhbNo={self.exhibition_no}",
                }
                if item not in collected:
                    collected.append(item)
        return collected

    async def _scan_region(self, page) -> List[Dict[str, Any]]:
        selects = await self._find_selects(page)
        if not selects:
            return await self._scan_region_custom_ui(page)

        sido_select = selects[0][0]
        sido_options = await self._get_select_options(sido_select)
        sido_candidates = [
            item["label"] for item in sido_options
            if item["label"] in SIDO_ORDER
        ] or [item["label"] for item in sido_options if item["label"] and item["label"] not in {"선택", "전체"}]

        results: List[Dict[str, Any]] = []
        for sido in sido_candidates:
            await sido_select.select_option(label=sido)
            await page.wait_for_timeout(900)
            await self._click_search(page)
            await page.wait_for_timeout(1500)

        for item in self._all_captured_api_items:
            results.append(self._normalize_api_item(item))
        return results

    async def _scan_region_custom_ui(self, page) -> List[Dict[str, Any]]:
        target_sido_raw = os.getenv("TEST_SIDO", "").strip()
        if target_sido_raw:
            parts = target_sido_raw.split(None, 1)
            target_sido = parts[0]
            target_sigun = parts[1] if len(parts) > 1 else ""
            sidos = [target_sido]
            print(f"지정된 단일 지역 검색: {target_sido_raw}")
        else:
            target_sigun = ""
            sidos = SIDO_ORDER
            print(f"전국 {len(sidos)}개 시/도 순회 조회를 시작합니다.")

        # If any cars were captured on initial page load (default region)
        if self._all_captured_api_items:
            print(f"기본 지역 로드 시 차량 {len(self._all_captured_api_items)}대 감지")

        for sido in sidos:
            trigger = page.locator("button:has-text('배송지역 변경')")
            if await trigger.count() == 0:
                print("배송지역 변경 버튼을 찾지 못했습니다.")
                break

            try:
                await trigger.first.click()
                await page.wait_for_timeout(500)
            except Exception as exc:
                print(f"배송지역 변경 클릭 실패: {exc}")
                break

            dialog = page.locator(".el-dialog").filter(has_text="배송지 변경")
            if await dialog.count() == 0:
                dialog = page.locator(".el-dialog:visible")
            if await dialog.count() == 0:
                print("배송지 변경 모달을 찾지 못했습니다.")
                break

            # 1. 배송지 시/도 선택
            sido_input = dialog.locator("input[placeholder='시/도']")
            if await sido_input.count() > 0:
                try:
                    await sido_input.click()
                    await page.wait_for_timeout(250)

                    sido_opt = page.locator(
                        ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                    ).filter(has_text=re.compile(rf"^\s*{re.escape(sido)}\s*$"))

                    if await sido_opt.count() == 0:
                        sido_opt = page.locator(
                            ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                        ).filter(has_text=sido)

                    if await sido_opt.count() > 0:
                        await sido_opt.first.click()
                        await page.wait_for_timeout(250)
                    else:
                        print(f"[{sido}] 옵션을 찾지 못했습니다.")
                        continue
                except Exception as exc:
                    print(f"[{sido}] 시/도 선택 실패: {exc}")
                    continue

                # 1-2. 배송지 시/군/구 선택 (첫 번째 도시 선택, 환경변수 target_sigun이 있을 때만 해당 시/군 선택)
                sigungu_input = dialog.locator("input[placeholder='시/군/구']")
                if await sigungu_input.count() > 0:
                    try:
                        await sigungu_input.click()
                        await page.wait_for_timeout(250)
                        sig_opts = page.locator(
                            ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                        )
                        if target_sigun and await sig_opts.filter(has_text=target_sigun).count() > 0:
                            await sig_opts.filter(has_text=target_sigun).first.click()
                        elif await sig_opts.count() > 0:
                            await sig_opts.first.click()
                        await page.wait_for_timeout(250)
                    except Exception:
                        pass

                # 2. 전기차 구매보조금 신청 지역 (경북 구미시로 고정)
                sub_sido_input = dialog.locator("input[placeholder='시/도 선택']")
                if await sub_sido_input.count() > 0:
                    try:
                        current_sub_sido = await sub_sido_input.input_value()
                        if current_sub_sido != SUBSIDY_SIDO:
                            await sub_sido_input.click()
                            await page.wait_for_timeout(200)

                            sub_sido_opt = page.locator(
                                ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                            ).filter(has_text=re.compile(rf"^\s*{re.escape(SUBSIDY_SIDO)}\s*$"))
                            if await sub_sido_opt.count() == 0:
                                sub_sido_opt = page.locator(
                                    ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                                ).filter(has_text=SUBSIDY_SIDO)

                            if await sub_sido_opt.count() > 0:
                                await sub_sido_opt.first.click()
                                await page.wait_for_timeout(250)

                        sub_sig_input = dialog.locator("input[placeholder='시/군 선택']")
                        if await sub_sig_input.count() > 0:
                            current_sub_sig = await sub_sig_input.input_value()
                            if current_sub_sig != SUBSIDY_SIGUN:
                                await sub_sig_input.click()
                                await page.wait_for_timeout(200)
                                sub_sig_opts = page.locator(
                                    ".el-select-dropdown:not([style*='display: none']) .el-select-dropdown__item"
                                )
                                sub_sig_target = sub_sig_opts.filter(has_text=SUBSIDY_SIGUN)
                                if await sub_sig_target.count() > 0:
                                    await sub_sig_target.first.click()
                                elif await sub_sig_opts.count() > 0:
                                    await sub_sig_opts.first.click()
                                await page.wait_for_timeout(200)
                    except Exception as exc:
                        if self._verbose():
                            print(f"[{sido}] 보조금 지역({SUBSIDY_SIDO} {SUBSIDY_SIGUN}) 설정 참고: {exc}")

                # 3. 변경 버튼 클릭하여 적용
                change_btn = dialog.locator("button:has-text('변경')")
                if await change_btn.count() > 0:
                    try:
                        await change_btn.click()
                        await page.wait_for_timeout(1000)
                        print(f"[{sido}] 배송지역 변경 완료 (현재 수집 누적: {len(self._all_captured_api_items)}대)")
                    except Exception as exc:
                        print(f"[{sido}] 변경 버튼 클릭 실패: {exc}")

        # 정규화 및 중복 제거
        results: List[Dict[str, Any]] = []
        seen_run_ids = set()

        for raw_item in self._all_captured_api_items:
            normalized = self._normalize_api_item(raw_item)
            vid = normalized["id"]
            if vid and vid not in seen_run_ids:
                seen_run_ids.add(vid)
                results.append(normalized)

        if not results:
            cards = await self._extract_result_cards(page)
            for card in cards:
                text = card.get("text", "")
                link = card.get("href", "")
                vid = self._dedupe_key(text, link)
                if vid not in seen_run_ids:
                    seen_run_ids.add(vid)
                    results.append({
                        "id": vid,
                        "name": text[:80],
                        "trim": "미상",
                        "color": "미상",
                        "price": 0,
                        "deliveryCenter": "미상",
                        "options": "",
                        "link": link,
                    })

        return results

    async def run(self) -> List[Dict[str, Any]]:
        if async_playwright is None:
            raise RuntimeError(
                "Playwright가 설치되지 않았습니다. pip install playwright 및 playwright install chromium 를 먼저 실행하세요."
            )

        headless = os.getenv("HEADLESS", "true").strip().lower() not in {"0", "false", "no"}
        save_debug = os.getenv("DEBUG_ARTIFACTS", "false").strip().lower() in {"1", "true", "yes"}

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless, args=launch_args)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            page = await context.new_page()
            page.on("response", self._capture_vehicle_response)
            try:
                await self._open_page(page)
                results = await self._scan_region(page)
                await self._print_network_candidates()
                if save_debug:
                    await page.screenshot(path="casper-debug.png", full_page=True)
                    Path("casper-debug.html").write_text(await page.content(), encoding="utf-8")
                    print("진단 파일 저장: casper-debug.png, casper-debug.html")
                return results
            finally:
                await context.close()
                await browser.close()

    def scan_once(self) -> List[Dict[str, Any]]:
        async def _inner() -> List[Dict[str, Any]]:
            return await self.run()
        return asyncio.run(_inner())


async def main() -> None:
    monitor = BrowserMonitor(exhibition_no=DEFAULT_EXHIBITION_NO, state_file="state.json")
    try:
        vehicles = await monitor.run()
        if not vehicles:
            print("선택하신 조건에 맞는 기획전 차량이 없습니다.")
            return
        for item in vehicles:
            print(item)
    except Exception as exc:
        print(f"브라우저 검색 중 오류: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
