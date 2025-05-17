from datetime import timedelta

import pytest
import responses
from django.utils import timezone

from api.models import Country, NameCountryProbability
from api.serializers import (
    CountrySerializer,
    NameCountryProbabilitySerializer,
    PopularNamesSerializer,
)


@pytest.fixture
def country_data():
    return {
        "code": "FR",
        "name": "France",
        "official_name": "French Republic",
        "region": "Europe",
        "subregion": "Western Europe",
        "independent": True,
        "capital_name": "Paris",
        "capital_latitude": 48.8566,
        "capital_longitude": 2.3522,
        "flag_png_url": "https://example.com/fr-flag.png",
        "flag_svg_url": "https://example.com/fr-flag.svg",
        "flag_alt": "French Flag",
    }


@pytest.fixture
def country(country_data):
    return Country.objects.create(**country_data)


@pytest.mark.django_db
class TestCountrySerializer:
    def test_serialize_country(self, country):
        serializer = CountrySerializer(country)
        data = serializer.data

        assert data["code"] == "FR"
        assert data["name"] == "France"
        assert data["official_name"] == "French Republic"
        assert data["capital_name"] == "Paris"
        assert data["capital_latitude"] == 48.8566
        assert data["capital_longitude"] == 2.3522

    def test_serialize_country_with_null_fields(self):
        country = Country.objects.create(
            code="XX",
            name="Test Country",
            official_name="Test Official Name",
            region="Test Region",
            subregion="Test Subregion",
        )
        serializer = CountrySerializer(country)
        data = serializer.data

        assert data["capital_name"] is None
        assert data["flag_png_url"] is None
        assert data["flag_svg_url"] is None

    def test_deserialize_country(self, country_data):
        serializer = CountrySerializer(data=country_data)
        assert serializer.is_valid()
        country = serializer.save()

        assert country.code == "FR"
        assert country.name == "France"
        assert country.capital_name == "Paris"


@pytest.mark.django_db
class TestNameCountryProbabilitySerializer:
    def test_serialize_name_probability(self, country):
        prob = NameCountryProbability.objects.create(
            name="Pierre",
            country=country,
            probability=0.85,
            count_of_requests=10,
            last_accessed=timezone.now(),
        )
        serializer = NameCountryProbabilitySerializer(prob)
        data = serializer.data

        assert data["name"] == "Pierre"
        assert data["probability"] == 0.85
        assert data["count_of_requests"] == 10
        assert data["country_details"]["code"] == "FR"
        assert data["country_details"]["name"] == "France"

    def test_get_or_fetch_probabilities_cached(self, country):
        prob = NameCountryProbability.objects.create(
            name="Jean",
            country=country,
            probability=0.9,
            count_of_requests=1,
            last_accessed=timezone.now(),
        )

        results = NameCountryProbabilitySerializer.get_or_fetch_probabilities("Jean")
        assert len(results) == 1
        assert results[0].name == "Jean"
        assert results[0].probability == 0.9
        assert results[0].id == prob.id

    @responses.activate
    def test_get_or_fetch_probabilities_new_name(self, country_data):
        responses.add(
            responses.GET,
            "https://api.nationalize.io/?name=Marie",
            json={"name": "Marie", "country": [{"country_id": "FR", "probability": 0.75}]},
            status=200,
        )

        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/alpha/FR",
            json=[
                {
                    "name": {"common": "France", "official": "French Republic"},
                    "region": "Europe",
                    "subregion": "Western Europe",
                    "capital": ["Paris"],
                    "capitalInfo": {"latlng": [48.8566, 2.3522]},
                }
            ],
            status=200,
        )

        results = NameCountryProbabilitySerializer.get_or_fetch_probabilities("Marie")
        assert len(results) == 1
        assert results[0].name == "Marie"
        assert results[0].probability == 0.75

    def test_get_or_fetch_probabilities_outdated(self, country):
        old_prob = NameCountryProbability.objects.create(
            name="Louis",
            country=country,
            probability=0.8,
            count_of_requests=1,
            last_accessed=timezone.now() - timedelta(days=2),
        )

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.nationalize.io/?name=Louis",
                json={"name": "Louis", "country": [{"country_id": "FR", "probability": 0.85}]},
                status=200,
            )

            results = NameCountryProbabilitySerializer.get_or_fetch_probabilities("Louis")
            assert len(results) == 1
            assert results[0].name == "Louis"
            assert results[0].probability == 0.85
            assert results[0].id == old_prob.id

    @responses.activate
    def test_get_or_fetch_probabilities_multiple_countries(self):
        responses.add(
            responses.GET,
            "https://api.nationalize.io/?name=Alex",
            json={
                "name": "Alex",
                "country": [
                    {"country_id": "US", "probability": 0.4},
                    {"country_id": "GB", "probability": 0.3},
                    {"country_id": "AU", "probability": 0.2},
                ],
            },
            status=200,
        )

        for country_code in ["US", "GB", "AU"]:
            responses.add(
                responses.GET,
                f"https://restcountries.com/v3.1/alpha/{country_code}",
                json=[
                    {
                        "name": {
                            "common": f"Test {country_code}",
                            "official": f"Test {country_code}",
                        },
                        "region": "Test Region",
                        "subregion": "Test Subregion",
                    }
                ],
                status=200,
            )

        results = NameCountryProbabilitySerializer.get_or_fetch_probabilities("Alex")
        assert len(results) == 3
        assert [r.probability for r in results] == [0.4, 0.3, 0.2]


@pytest.mark.django_db
class TestPopularNamesSerializer:
    def test_serialize_popular_names(self):
        data = {"name": "Test", "total_requests": 42}
        serializer = PopularNamesSerializer(data)

        assert serializer.data["name"] == "Test"
        assert serializer.data["total_requests"] == 42

    def test_get_popular_names_ordering(self, country):
        names_data = [("Name1", 5), ("Name2", 10), ("Name3", 3)]

        for name, count in names_data:
            NameCountryProbability.objects.create(
                name=name,
                country=country,
                probability=0.5,
                count_of_requests=count,
                last_accessed=timezone.now(),
            )

        results = PopularNamesSerializer.get_popular_names(country.code)
        assert len(results) == 3
        assert results[0]["name"] == "Name2"
        assert results[0]["total_requests"] == 10

    def test_get_popular_names_limit(self, country):
        for i in range(7):
            NameCountryProbability.objects.create(
                name=f"Name{i}",
                country=country,
                probability=0.5,
                count_of_requests=10 - i,
                last_accessed=timezone.now(),
            )

        results = PopularNamesSerializer.get_popular_names(country.code)
        assert len(results) == 5
