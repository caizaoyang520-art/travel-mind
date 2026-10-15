import httpx
from pydantic import BaseModel

from travel_mind.config import get_settings


class AmapApiError(RuntimeError):
    """高德 API 调用异常。"""


class AmapCity(BaseModel):
    city: str
    adcode: str
    location: str
    formatted_address: str


class AmapWeatherForecast(BaseModel):
    date: str
    day_weather: str
    night_weather: str
    day_temperature: str
    night_temperature: str
    day_wind: str
    night_wind: str
    day_power: str
    night_power: str


class AmapPoi(BaseModel):
    id: str
    name: str
    address: str = ""
    location: str
    poi_type: str = ""
    city_name: str = ""
    district_name: str = ""
    telephone: str | None = None


class AmapWalkingRoute(BaseModel):
    distance_meters: int
    """步行距离，单位米。"""
    duration_seconds: int
    """预计步行耗时，单位秒。"""
    instructions: list[str]
    """分步导航指引。"""


class AmapClient:
    def __init__(self) -> None:
        settings = get_settings()

        if settings.amap_api_key is None:
            raise AmapApiError(
                "未配置 AMAP_API_KEY，请先在 .env 中填写高德 Web 服务 Key"
            )

        self._api_key = settings.amap_api_key.get_secret_value()
        self._client = httpx.Client(
            base_url=settings.amap_base_url,
            timeout=15,
        )

    def _get(self, path: str, params: dict[str, str]) -> dict:
        response = self._client.get(
            path,
            params={
                "key": self._api_key,
                "output": "JSON",
                **params,
            },
        )
        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "1":
            raise AmapApiError(
                f"高德 API 调用失败："
                f"{payload.get('info')}，"
                f"错误码：{payload.get('infocode')}"
            )

        return payload

    def geocode_city(self, city: str) -> AmapCity:
        """查询城市的行政编码和经纬度。"""

        payload = self._get(
            "/v3/geocode/geo",
            {
                "address": city,
                "city": city,
            },
        )

        geocodes = payload.get("geocodes", [])

        if not geocodes:
            raise AmapApiError(f"没有找到城市：{city}")

        item = geocodes[0]

        return AmapCity(
            city=item.get("city") or city,
            adcode=item["adcode"],
            location=item["location"],
            formatted_address=item["formatted_address"],
        )

    def get_weather_forecast(
        self,
        adcode: str,
    ) -> list[AmapWeatherForecast]:
        """查询城市未来天气预报。"""

        payload = self._get(
            "/v3/weather/weatherInfo",
            {
                "city": adcode,
                "extensions": "all",
            },
        )

        forecasts = payload.get("forecasts", [])

        if not forecasts:
            raise AmapApiError(f"没有找到天气预报：{adcode}")

        casts = forecasts[0].get("casts", [])

        return [
            AmapWeatherForecast(
                date=item["date"],
                day_weather=item["dayweather"],
                night_weather=item["nightweather"],
                day_temperature=item["daytemp"],
                night_temperature=item["nighttemp"],
                day_wind=item["daywind"],
                night_wind=item["nightwind"],
                day_power=item["daypower"],
                night_power=item["nightpower"],
            )
            for item in casts
        ]

    def search_pois(
        self,
        keywords: str,
        city: str,
        page: int = 1,
        page_size: int = 10,
    ) -> list[AmapPoi]:
        """按关键词搜索城市内的景点、餐厅等 POI。"""

        payload = self._get(
            "/v3/place/text",
            {
                "keywords": keywords,
                "city": city,
                "citylimit": "true",
                "offset": str(min(page_size, 25)),
                "page": str(page),
                "extensions": "all",
            },
        )

        pois = payload.get("pois", [])

        return [
            AmapPoi(
                id=item["id"],
                name=item["name"],
                address=item.get("address") or "",
                location=item["location"],
                poi_type=item.get("type") or "",
                city_name=item.get("cityname") or "",
                district_name=item.get("adname") or "",
                telephone=item.get("tel") or None,
            )
            for item in pois
        ]

    def get_walking_route(
        self,
        origin: str,
        destination: str,
    ) -> AmapWalkingRoute:
        """查询两个经纬度之间的步行路线。"""

        payload = self._get(
            "/v5/direction/walking",
            {
                "origin": origin,
                "destination": destination,
                "show_fields": "cost",
            },
        )

        paths = payload.get("route", {}).get("paths", [])

        if not paths:
            raise AmapApiError(f"没有找到步行路线：{origin} → {destination}")

        path = paths[0]
        cost = path.get("cost") or {}
        steps = path.get("steps") or []

        return AmapWalkingRoute(
            distance_meters=int(path.get("distance") or 0),
            duration_seconds=int(cost.get("duration") or 0),
            instructions=[
                step["instruction"] for step in steps if step.get("instruction")
            ],
        )

    def close(self) -> None:
        self._client.close()
