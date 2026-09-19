import json
from typing import Any, Dict, List

import requests


class CasperClient:
    SIDO_CODES = {
        "서울": "B",
        "부산": "C",
        "대구": "D",
        "인천": "E",
        "광주": "F",
        "대전": "G",
        "울산": "H",
        "세종": "J",
        "경기": "K",
        "강원": "M",
        "충북": "N",
        "충남": "P",
        "전북": "Q",
        "전남": "R",
        "경북": "S",
        "경남": "T",
        "제주": "U",
    }

    def __init__(self, exhibition_no: str = "E20260133"):
        self.exhibition_no = exhibition_no
        self.base_url = "https://casper.hyundai.com/gw/wp/product/v2/product/exhibition/cars"
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ko-KR,ko;q=0.9,en;q=0.8",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://casper.hyundai.com",
            "referer": f"https://casper.hyundai.com/vehicles/car-list/promotion?exhbNo={exhibition_no}",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }

    def fetch_cars(self) -> List[Dict[str, Any]]:
        return self.fetch_cars_with_region("", "")

    def fetch_cars_with_region(self, delivery_area_code: str = "", delivery_local_area_code: str = "") -> List[Dict[str, Any]]:
        payload = {
            "exhbNo": self.exhibition_no,
            "param": {
                "carCode": "",
                "deliveryAreaCode": delivery_area_code,
                "deliveryLocalAreaCode": delivery_local_area_code,
                "pageNo": 1,
                "pageSize": 100,
                "sortCode": "10",
            },
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"Request failed while fetching Casper cars for area={delivery_area_code}, sigun={delivery_local_area_code}: {exc}")
            return []

        if response.status_code != 200:
            print(f"Hyundai API returned status {response.status_code} for area={delivery_area_code}, sigun={delivery_local_area_code}: {response.text[:500]}")
            return []

        try:
            data = response.json()
        except ValueError:
            print(f"Invalid JSON from Hyundai API for area={delivery_area_code}, sigun={delivery_local_area_code}: {response.text[:500]}")
            return []

        if isinstance(data, dict):
            items = data.get("result", {}).get("items")
            if items is not None:
                return items
            if "cars" in data:
                return data.get("cars", [])
            if "list" in data:
                return data.get("list", [])

        if isinstance(data, list):
            return data

        print(f"Unexpected response structure from Hyundai API for area={delivery_area_code}, sigun={delivery_local_area_code}: {str(data)[:500]}")
        return []

    def fetch_all_sido_first_sigun_cars(self) -> List[Dict[str, Any]]:
        seen_ids = set()
        collected: List[Dict[str, Any]] = []

        for sido_name, sido_code in self.SIDO_CODES.items():
            local_area_code = f"{sido_code}0"
            cars = self.fetch_cars_with_region(sido_code, local_area_code)
            if not cars:
                print(f"선택하신 조건에 맞는 기획전 차량이 없습니다: {sido_name}({sido_code}/{local_area_code})")
                continue
            for car in cars:
                normalized = self.normalize_car(car)
                vehicle_id = normalized.get("id")
                if vehicle_id and vehicle_id not in seen_ids:
                    seen_ids.add(vehicle_id)
                    collected.append(normalized)

        return collected

    def normalize_car(self, car: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(car.get("carCode") or car.get("id") or car.get("carId") or car.get("productCode") or json.dumps(car, ensure_ascii=False)),
            "name": car.get("carName") or car.get("modelName") or "미상",
            "trim": car.get("carTrimName") or car.get("trimName") or "미상",
            "color": car.get("exteriorColorName") or car.get("colorName") or "미상",
            "price": car.get("finalAmount") or car.get("salePrice") or car.get("price") or 0,
            "deliveryCenter": car.get("deliveryCenterName") or car.get("deliveryCenter") or "미상",
            "link": car.get("detailUrl") or f"https://casper.hyundai.com/vehicles/car-list/promotion?exhbNo={self.exhibition_no}",
        }
