"""Tests for the PollenDK API client."""

from __future__ import annotations

import json
from typing import Any, Self
from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.pollen_dk.api import (
    PollenDKApi,
    PollenDKApiError,
    get_severity,
)

from .conftest import MOCK_FIRESTORE_RESPONSE

# ── Helpers ───────────────────────────────────────────────────────────────────


class _MockResponse:
    """Minimal aiohttp ClientResponse stand-in."""

    def __init__(self, data: Any, status: int = 200) -> None:
        self._data = data
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
                message="Error",
            )

    async def json(self, **_kwargs: Any) -> Any:
        return self._data

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass


def _make_session(data: Any, status: int = 200) -> MagicMock:
    session = MagicMock()
    session.get.return_value = _MockResponse(data, status)
    return session


# ── get_severity ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("count", "pollen_type", "expected"),
    [
        (None, "birk", "unknown"),
        (-1, "birk", "unknown"),
        (0, "birk", "none"),
        (1, "birk", "low"),
        (5, "birk", "low"),
        (6, "birk", "moderate"),
        (50, "birk", "moderate"),
        (51, "birk", "high"),
        (500, "birk", "high"),
        (501, "birk", "very_high"),
        (0, "bynke", "none"),
        (5, "bynke", "low"),
        (10, "bynke", "moderate"),
        (30, "bynke", "high"),
        (0, "alternaria", "none"),
        (100, "alternaria", "low"),
        (1000, "alternaria", "moderate"),
        (5000, "alternaria", "high"),
        (50001, "cladosporium", "very_high"),
        # Unknown pollen type falls back to birk thresholds
        (0, "unknown_type", "none"),
        (501, "unknown_type", "very_high"),
    ],
)
def test_get_severity(count, pollen_type, expected) -> None:
    assert get_severity(pollen_type, count) == expected


# ── _firestore_value ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        ({"stringValue": "hello"}, "hello"),
        ({"stringValue": ""}, ""),
        ({"integerValue": "42"}, 42),
        ({"integerValue": "-1"}, -1),
        ({"doubleValue": 3.14}, 3.14),
        ({"booleanValue": True}, True),
        ({"booleanValue": False}, False),
        ({"nullValue": None}, None),
        # Non-dict passes through unchanged
        ("plain string", "plain string"),
        (123, 123),
        (None, None),
    ],
)
def test_firestore_value_scalars(node, expected) -> None:
    assert PollenDKApi._firestore_value(node) == expected


def test_firestore_value_map() -> None:
    node = {
        "mapValue": {"fields": {"a": {"stringValue": "b"}, "n": {"integerValue": "7"}}}
    }
    assert PollenDKApi._firestore_value(node) == {"a": "b", "n": 7}


def test_firestore_value_empty_map() -> None:
    assert PollenDKApi._firestore_value({"mapValue": {}}) == {}


def test_firestore_value_array() -> None:
    node = {"arrayValue": {"values": [{"integerValue": "1"}, {"integerValue": "2"}]}}
    assert PollenDKApi._firestore_value(node) == [1, 2]


def test_firestore_value_empty_array() -> None:
    assert PollenDKApi._firestore_value({"arrayValue": {}}) == []


def test_firestore_value_nested() -> None:
    node = {
        "mapValue": {
            "fields": {
                "child": {"mapValue": {"fields": {"leaf": {"stringValue": "value"}}}}
            }
        }
    }
    assert PollenDKApi._firestore_value(node) == {"child": {"leaf": "value"}}


# ── _parse_response ───────────────────────────────────────────────────────────


def test_parse_response_returns_both_regions() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    assert set(result.keys()) == {"koebenhavn", "viborg"}


def test_parse_response_koebenhavn_birk() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    birk = result["koebenhavn"]["birk"]
    assert birk["count"] == 186
    assert birk["severity"] == "high"
    assert birk["name_en"] == "Birch"


def test_parse_response_viborg_birk() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    birk = result["viborg"]["birk"]
    assert birk["count"] == 60
    assert birk["severity"] == "high"


def test_parse_response_out_of_season_is_none() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    for pollen_key in (
        "bynke",
        "el",
        "elm",
        "graes",
        "hassel",
        "alternaria",
        "cladosporium",
    ):
        entry = result["koebenhavn"][pollen_key]
        assert entry["count"] is None, f"{pollen_key} should have no count"
        assert entry["severity"] == "unknown"


def test_parse_response_all_pollen_types_present() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    expected_keys = {
        "birk",
        "bynke",
        "el",
        "elm",
        "graes",
        "hassel",
        "alternaria",
        "cladosporium",
    }
    assert set(result["koebenhavn"].keys()) >= expected_keys


def test_parse_response_date_preserved() -> None:
    api = PollenDKApi(MagicMock())
    result = api._parse_response(MOCK_FIRESTORE_RESPONSE)
    assert result["koebenhavn"]["last_update"] == "26-04-2026"


def test_parse_response_unknown_station_ignored() -> None:
    api = PollenDKApi(MagicMock())
    data = {
        "fields": {
            "99": {
                "mapValue": {
                    "fields": {
                        "date": {"stringValue": "01-01-2026"},
                        "data": {"mapValue": {"fields": {}}},
                    }
                }
            },
        }
    }
    result = api._parse_response(data)
    assert result == {}


def test_parse_response_non_dict_returns_empty() -> None:
    api = PollenDKApi(MagicMock())
    assert api._parse_response("not a dict") == {}
    assert api._parse_response([]) == {}


def test_parse_response_missing_fields_returns_empty() -> None:
    api = PollenDKApi(MagicMock())
    assert api._parse_response({}) == {}


# ── async_get_pollen_data ─────────────────────────────────────────────────────


async def test_async_get_pollen_data_success() -> None:
    session = _make_session(MOCK_FIRESTORE_RESPONSE)
    api = PollenDKApi(session)
    result = await api.async_get_pollen_data()
    assert "koebenhavn" in result
    assert result["koebenhavn"]["birk"]["count"] == 186


async def test_async_get_pollen_data_double_encoded() -> None:
    """API sometimes returns the Firestore document wrapped in an extra JSON string."""
    double_encoded = json.dumps(MOCK_FIRESTORE_RESPONSE)
    session = _make_session(double_encoded)
    api = PollenDKApi(session)
    result = await api.async_get_pollen_data()
    assert "koebenhavn" in result


async def test_async_get_pollen_data_http_error() -> None:
    session = _make_session({}, status=500)
    api = PollenDKApi(session)
    with pytest.raises(PollenDKApiError, match="HTTP error"):
        await api.async_get_pollen_data()


async def test_async_get_pollen_data_network_error() -> None:
    session = MagicMock()
    session.get.side_effect = aiohttp.ClientConnectionError("connection refused")
    api = PollenDKApi(session)
    with pytest.raises(PollenDKApiError, match="Network error"):
        await api.async_get_pollen_data()
