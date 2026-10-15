import json
from types import SimpleNamespace

import pytest

from travel_mind.tools.amap_tools import (
    get_city_weather,
    get_walking_route,
    search_city_pois,
)


class FakeAmapClient:
    def __init__(self) -> None:
        self.search_arguments: dict = {}
        self.closed = False

    def search_pois(
        self,
        **kwargs,
    ) -> list:
        self.search_arguments = kwargs

        return [
            SimpleNamespace(
                model_dump=lambda: {
                    "name": "西湖",
                    "address": "杭州市西湖区",
                }
            )
        ]

    def close(self) -> None:
        self.closed = True


def test_search_city_pois_tool(
    monkeypatch,
) -> None:
    client = FakeAmapClient()

    monkeypatch.setattr(
        "travel_mind.tools.amap_tools.AmapClient",
        lambda: client,
    )

    result = search_city_pois.invoke(
        {
            "city": "杭州",
            "keywords": "景点",
            "limit": 100,
        }
    )

    assert client.search_arguments == {
        "keywords": "景点",
        "city": "杭州",
        "page_size": 10,
    }
    assert client.closed is True
    assert json.loads(result) == [
        {
            "name": "西湖",
            "address": "杭州市西湖区",
        }
    ]


class FakeWeatherClient:
    def __init__(self) -> None:
        self.received_adcode: str | None = None
        self.closed = False

    def geocode_city(
        self,
        city: str,
    ) -> SimpleNamespace:
        assert city == "杭州"

        return SimpleNamespace(
            city="杭州市",
            adcode="330100",
        )

    def get_weather_forecast(
        self,
        adcode: str,
    ) -> list:
        self.received_adcode = adcode

        return [
            SimpleNamespace(
                model_dump=lambda: {
                    "date": "2026-10-20",
                    "day_weather": "晴",
                }
            )
        ]

    def close(self) -> None:
        self.closed = True


def test_get_city_weather_tool(
    monkeypatch,
) -> None:
    client = FakeWeatherClient()

    monkeypatch.setattr(
        "travel_mind.tools.amap_tools.AmapClient",
        lambda: client,
    )

    result = get_city_weather.invoke(
        {
            "city": "杭州",
        }
    )

    body = json.loads(result)

    assert body["city"] == "杭州市"
    assert body["adcode"] == "330100"
    assert body["forecasts"][0]["day_weather"] == "晴"
    assert client.received_adcode == "330100"
    assert client.closed is True


class FakeWalkingClient:
    def __init__(self) -> None:
        self.received_arguments: dict = {}
        self.closed = False

    def get_walking_route(
        self,
        **kwargs,
    ) -> SimpleNamespace:
        self.received_arguments = kwargs

        return SimpleNamespace(
            model_dump_json=lambda: '{"distance": 1200, "duration": 900}'
        )

    def close(self) -> None:
        self.closed = True


def test_get_walking_route_tool(
    monkeypatch,
) -> None:
    client = FakeWalkingClient()

    monkeypatch.setattr(
        "travel_mind.tools.amap_tools.AmapClient",
        lambda: client,
    )

    result = get_walking_route.invoke(
        {
            "origin": "120.123,30.234",
            "destination": "120.456,30.567",
        }
    )

    assert client.received_arguments == {
        "origin": "120.123,30.234",
        "destination": "120.456,30.567",
    }
    assert json.loads(result) == {
        "distance": 1200,
        "duration": 900,
    }
    assert client.closed is True


class FailingAmapClient:
    def __init__(self) -> None:
        self.closed = False

    def search_pois(
        self,
        **kwargs,
    ) -> list:
        raise RuntimeError("模拟高德连接失败")

    def close(self) -> None:
        self.closed = True


def test_amap_client_closes_after_error(
    monkeypatch,
) -> None:
    client = FailingAmapClient()

    monkeypatch.setattr(
        "travel_mind.tools.amap_tools.AmapClient",
        lambda: client,
    )

    with pytest.raises(
        RuntimeError,
        match="模拟高德连接失败",
    ):
        search_city_pois.invoke(
            {
                "city": "杭州",
                "keywords": "景点",
            }
        )

    assert client.closed is True
