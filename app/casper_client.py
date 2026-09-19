import json
from typing import Any, Dict, List

import requests


class CasperClient:
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
        payload = {
            "exhbNo": self.exhibition_no,
            "param": {
                "carCode": "",
                "deliveryAreaCode": "",
                "deliveryLocalAreaCode": "",
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
            print(f"Request failed while fetching Casper cars: {exc}")
            return []

        if response.status_code != 200:
            print(f"Hyundai API returned status {response.status_code}: {response.text[:500]}")
            return []

        try:
            data = response.json()
        except ValueError:
            print(f"Invalid JSON from Hyundai API: {response.text[:500]}")
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

        print(f"Unexpected response structure from Hyundai API: {str(data)[:500]}")
        return []

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
