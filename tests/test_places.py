from pathlib import Path

import pytest

from skills_gps.places import PlaceMatcher, is_remote

PLACES = PlaceMatcher.load(Path("data/places.toml"))


@pytest.mark.parametrize(
    ("place", "expected"),
    [
        ("San Francisco, CA", "US"),
        ("Some Small Town, CA", "US"),
        ("Toronto, ON, CA", "CA"),
        ("Toronto, CA", "CA"),
        ("Toronto, CA, New York", "CA US"),
        ("Berlin, DE", "DE"),
        ("Wilmington, DE", "US"),
        ("Bengaluru, IN", "IN"),
        ("Tel Aviv, IL", "IL"),
        ("Dublin", "IE"),
        ("Dublin, OH", "US"),
        ("Dublin, IE", "IE"),
        ("London, Ontario, Canada", "CA"),
        ("Cambridge, MA", "US"),
        ("Vancouver, Washington, United States", "US"),
        ("Atlanta, Georgia", "US"),
        ("Alpharetta, Georgia", "US"),
        ("Tbilisi, Georgia", "GE"),
        ("Albuquerque, New Mexico", "US"),
        ("São Paulo", "BR"),
        ("Germany - Berlin", "DE"),
        ("ES - Barcelona, Spain", "ES"),
        ("New York, US, New York", "US"),
        ("Remote U.S.", "US"),
        ("iso:GB", "GB"),
        ("Cary,North Carolina,United States", "US"),
        ("Seattle, San Francisco, New York City", "US"),
        ("Hong Kong; Singapore; Taiwan", "HK SG TW"),
        ("Remote (United States | Canada)", "US CA"),
        ("Cardiff, London or Remote (UK)", "GB"),
        ("Portland, OR, or Remote within Canada or United States", "US CA"),
        ("Dublin, Ireland, London, UK", "IE GB"),
    ],
)
def test_countries(place, expected):
    assert PLACES.countries([place]) == set(expected.split())


@pytest.mark.parametrize(
    "place", ["", "N/A", "Hybrid", "EMEA", "Georgia", "CA", "Contact us", "iso:ZZ"]
)
def test_unclear_places_stay_unknown(place):
    assert PLACES.countries([place]) == set()


def test_remote():
    assert is_remote(["Berlin", "Remote - EMEA"])
    assert is_remote(["US-Remote"])
    assert not is_remote(["Hybrid - Berlin"])
    assert not is_remote(["Not remote"])
