import asyncio
import hashlib
import json
import os
import re
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
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]


class BrowserMonitor:
    def __init__(self, exhibition_no: str = DEFAULT_EXHIBITION_NO, state_file: str = "state.json") -> None:
        self.exhibition_no = (exhibition_no or DEFAULT_EXHIBITION_NO).strip()
        self.state_file = state_file
        self._latest_api_items: List[Dict[str, Any]] = []

    def load_seen(self) -> set[str]:
        path = Path(self.state_file)
        if not path.exists():
            return set()
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    return {str(item) for item in data}
        except Exception:
            pass
        return set()

    def save_seen(self, ids: Sequence[str]) -> None:
        path = Path(self.state_file)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(list(dict.fromkeys(str(item) for item in ids)), handle, ensure_ascii=False, indent=2)

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
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

    async def _capture_vehicle_response(self, response) -> None:
        try:
            payload = await response.json()
        except Exception:
            return
        items = self._find_vehicle_items(payload)
        if isinstance(items, list):
            self._latest_api_items = [item for item in items if isinstance(item, dict)]

    @classmethod
    def _find_vehicle_items(cls, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                vehicle_keys = {"carCode", "carName", "modelName", "productCode", "carId"}
                if any(vehicle_keys.intersection(item.keys()) for item in value):
                    return value
            for item in value:
                found = cls._find_vehicle_items(item)
                if found:
                    return found
        elif isinstance(value, dict):
            for item in value.values():
                found = cls._find_vehicle_items(item)
                if found:
                    return found
        return []

    def _normalize_api_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        vehicle_id = str(
            item.get("carCode")
            or item.get("id")
            or item.get("carId")
            or item.get("productCode")
            or json.dumps(item, ensure_ascii=False, sort_keys=True)
        )
        name = item.get("carName") or item.get("modelName") or item.get("name") or "미상"
        trim = item.get("carTrimName") or item.get("trimName") or item.get("trim") or "미상"
        color = item.get("exteriorColorName") or item.get("colorName") or item.get("color") or "미상"
        link = item.get("detailUrl") or f"{BASE_URL}?exhbNo={self.exhibition_no}"
        return {
            "id": vehicle_id,
            "name": str(name),
            "trim": str(trim),
            "color": str(color),
            "price": item.get("finalAmount") or item.get("salePrice") or item.get("price") or 0,
            "deliveryCenter": item.get("deliveryCenterName") or item.get("deliveryCenter") or "미상",
            "link": str(link),
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

    async def _get_available_sidos(self, page) -> List[str]:
        result = await page.evaluate("""
            () => {
                try {
                    const raw = window.__NUXT__?.state?.commonModules?.addressSiDoList?.data;
                    if (Array.isArray(raw)) {
                        const names = raw
                            .map(item => item?.codeName || item?.name || item?.label || '')
                            .filter(Boolean)
                            .map(String);
                        return [...new Set(names)];
                    }
                } catch (error) {
                    return [];
                }
                return [];
            }
        """)
        if result:
            return [str(item).strip() for item in result if str(item).strip()]

        return [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ]

    async def _is_no_result(self, page) -> bool:
        text = await page.locator("body").inner_text()
        no_result_patterns = [
            "선택하신 조건에 맞는 기획전 차량이 없습니다",
            "해당 조건에 맞는 차량이 없습니다",
            "검색 결과가 없습니다",
            "차량이 없습니다",
        ]
        normalized = text or ""
        return any(pattern in normalized for pattern in no_result_patterns)

    async def _extract_result_cards(self, page) -> List[Dict[str, Any]]:
        selectors = [
            "article",
            "li",
            "tr",
            ".car-item",
            ".product-item",
            ".vehicle-item",
            "[data-car-code]",
            "a[href*='vehicle']",
            "a[href*='car']",
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
                if len(text) < 5:
                    continue
                href = None
                if await card.locator("a").count() > 0:
                    href = await card.locator("a").first.get_attribute("href")
                if href and ("javascript:" in href.lower() or href.startswith("#")):
                    href = None
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

        sido_select = None
        sigungu_select = None
        for locator, labels in selects:
            normalized = [self._clean_option_label(label) for label in labels if self._clean_option_label(label)]
            if sido_select is None and any(label in SIDO_ORDER for label in normalized):
                sido_select = locator
                continue
            if sigungu_select is None and locator != sido_select:
                sigungu_select = locator

        if sido_select is None:
            sido_select = selects[0][0]

        sido_options = await self._get_select_options(sido_select)
        sido_candidates = [
            item["label"] for item in sido_options
            if item["label"] in SIDO_ORDER
        ]

        if not sido_candidates:
            sido_candidates = [
                item["label"] for item in sido_options
                if item["label"] and item["label"] not in {"선택", "전체", "시/도 선택"}
            ]

        results: List[Dict[str, Any]] = []
        seen_ids = self.load_seen()

        for sido in sido_candidates:
            try:
                await sido_select.select_option(label=sido)
                await page.wait_for_timeout(900)
            except Exception:
                option_values = await self._get_select_options(sido_select)
                for item in option_values:
                    if item["label"] == sido:
                        await sido_select.select_option(value=item["value"] or item["label"])
                        break
                await page.wait_for_timeout(900)

            sigun_options = await self._get_sigun_options(sigungu_select)
            if not sigun_options:
                sigun_options = [{"label": sido, "value": ""}]

            for sigun in sigun_options:
                if sigungu_select is not None and sigun["value"]:
                    await sigungu_select.select_option(value=sigun["value"])
                print(f"{sido} / {sigun['label']} 조회 중")
                self._latest_api_items = []
                await self._click_search(page)
                await page.wait_for_timeout(1500)

                api_items = [self._normalize_api_item(item) for item in self._latest_api_items]
                if api_items:
                    print(f"{sido} / {sigun['label']}: 차량 API {len(api_items)}대 수신")
                if not api_items and await self._is_no_result(page):
                    print(f"{sido} / {sigun['label']}: 선택하신 조건에 맞는 기획전 차량이 없습니다.")
                    continue
                cards = api_items or await self._extract_result_cards(page)
                for card in cards:
                    if api_items:
                        vehicle_id = card["id"]
                        text = self._clean_option_label(
                            f"{card['name']} {card['trim']} {card['color']}"
                        )
                        link = card["link"]
                    else:
                        text = self._clean_option_label(card.get("text", ""))
                        link = card.get("href") or f"{BASE_URL}?exhbNo={self.exhibition_no}"
                        vehicle_id = self._dedupe_key(text, link)
                    if not text:
                        continue
                    if vehicle_id in seen_ids:
                        continue
                    seen_ids.add(vehicle_id)
                    results.append({
                        "id": vehicle_id,
                        "name": card.get("name", text[:80]),
                        "trim": card.get("trim", "미상"),
                        "color": card.get("color", "미상"),
                        "price": card.get("price", 0),
                        "deliveryCenter": card.get("deliveryCenter", sigun["label"]),
                        "link": link,
                        "region": f"{sido} {sigun['label']}",
                    })

        self.save_seen(sorted(seen_ids))
        return results

    async def _scan_region_custom_ui(self, page) -> List[Dict[str, Any]]:
        body_text = await page.locator("body").inner_text()
        normalized_body = self._clean_option_label(body_text)

        current_region = "서울특별시"
        if "서울 기준으로 검색합니다" in normalized_body:
            current_region = "서울"
        elif "서울특별시 기준으로 검색합니다" in normalized_body:
            current_region = "서울특별시"

        sidos = await self._get_available_sidos(page)
        if not sidos:
            sidos = [current_region]
            print(f"커스텀 UI에서 시/도를 직접 찾지 못해 기본 지역 {current_region}으로 조회합니다.")
        else:
            print(f"페이지 상태에서 확인된 시/도 목록: {sidos}")

        results: List[Dict[str, Any]] = []
        seen_ids = self.load_seen()

        for sido in sidos:
            trigger = page.locator(
                "button, a, [role='button'], [role='combobox']"
            ).filter(has_text=re.compile(r"배송\s*지역|배송지|주소|지역\s*변경|변경\s*지역"))
            print(f"{sido} 지역 변경 버튼 {await trigger.count()}개")
            if await trigger.count() > 0:
                try:
                    await trigger.first.click()
                    await page.wait_for_timeout(1200)
                except Exception:
                    pass
            else:
                print("지역 변경 버튼을 찾지 못했습니다.")

            region_match = page.locator(
                "button, a, li, [role='button'], [role='option']"
            ).filter(has_text=re.compile(rf"^\s*{re.escape(sido)}\s*$"))
            print(f"{sido} 지역 선택 요소 {await region_match.count()}개")
            if await region_match.count() > 0:
                try:
                    await region_match.first.click()
                    await page.wait_for_timeout(900)
                except Exception:
                    pass
            else:
                print(f"{sido} 지역 선택 요소를 찾지 못했습니다.")

            self._latest_api_items = []
            await self._click_search(page)
            await page.wait_for_timeout(1500)

            api_items = [self._normalize_api_item(item) for item in self._latest_api_items]
            if api_items:
                print(f"{sido}: 차량 API {len(api_items)}대 수신")
            if not api_items and await self._is_no_result(page):
                print(f"{sido}: 선택하신 조건에 맞는 기획전 차량이 없습니다.")
                continue
            cards = api_items or await self._extract_result_cards(page)
            for card in cards:
                if api_items:
                    vehicle_id = card["id"]
                    text = self._clean_option_label(f"{card['name']} {card['trim']} {card['color']}")
                    link = card["link"]
                else:
                    text = self._clean_option_label(card.get("text", ""))
                    link = card.get("href") or f"{BASE_URL}?exhbNo={self.exhibition_no}"
                    vehicle_id = self._dedupe_key(text, link)
                if not text:
                    continue
                if vehicle_id in seen_ids:
                    continue
                seen_ids.add(vehicle_id)
                results.append({
                    "id": vehicle_id,
                    "name": card.get("name", text[:80]),
                    "trim": card.get("trim", "미상"),
                    "color": card.get("color", "미상"),
                    "price": card.get("price", 0),
                    "deliveryCenter": card.get("deliveryCenter", sido),
                    "link": link,
                    "region": sido,
                })

        self.save_seen(sorted(seen_ids))
        return results

    async def run(self) -> List[Dict[str, Any]]:
        if async_playwright is None:
            raise RuntimeError("Playwright가 설치되지 않았습니다. pip install playwright 및 playwright install chromium 를 먼저 실행하세요.")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1600, "height": 1200})
            page.on("response", self._capture_vehicle_response)
            try:
                await self._open_page(page)
                return await self._scan_region(page)
            finally:
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
