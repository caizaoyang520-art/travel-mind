import json

from langchain_core.tools import tool

from travel_mind.tools.amap_client import AmapClient


@tool
def get_city_weather(city: str) -> str:
    """查询中国城市未来几天的天气预报。city 应为城市中文名，例如杭州。"""

    client = AmapClient()

    try:
        city_info = client.geocode_city(city)
        forecasts = client.get_weather_forecast(city_info.adcode)

        result = {
            "city": city_info.city,
            "adcode": city_info.adcode,
            "forecasts": [forecast.model_dump() for forecast in forecasts],
        }

        return json.dumps(result, ensure_ascii=False)
    finally:
        client.close()


@tool
def search_city_pois(
    city: str,
    keywords: str,
    limit: int = 6,
) -> str:
    """搜索指定城市的景点、餐厅等地点。keywords 可以是景点、博物馆、杭帮菜等。"""

    client = AmapClient()

    try:
        pois = client.search_pois(
            keywords=keywords,
            city=city,
            page_size=max(1, min(limit, 10)),
        )

        result = [poi.model_dump() for poi in pois]

        return json.dumps(result, ensure_ascii=False)
    finally:
        client.close()


@tool
def get_walking_route(
    origin: str,
    destination: str,
) -> str:
    """
    查询两个地点之间的步行路线。

    origin 和 destination 必须是“经度,纬度”格式，
    应先通过 search_city_pois 获得地点坐标。
    """

    client = AmapClient()

    try:
        route = client.get_walking_route(
            origin=origin,
            destination=destination,
        )

        return route.model_dump_json()
    finally:
        client.close()


AMAP_TOOLS = [
    get_city_weather,
    search_city_pois,
    get_walking_route,
]
