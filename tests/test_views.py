import urllib.parse
from datetime import timedelta

import pytest
import requests
import responses
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.models import Country, NameCountryProbability


@pytest.fixture
def country():
    return Country.objects.create(
        code="US",
        name="United States",
        official_name="United States of America",
        region="Americas",
        subregion="North America",
        independent=True,
        capital_name="Washington, D.C.",
        capital_latitude=38.895,
        capital_longitude=-77.0366,
        flag_png_url="https://example.com/us-flag.png",
        flag_svg_url="https://example.com/us-flag.svg",
        flag_alt="US Flag",
    )


@pytest.fixture
def uk_country():
    return Country.objects.create(
        code="GB",
        name="United Kingdom",
        official_name="United Kingdom of Great Britain and Northern Ireland",
        region="Europe",
        subregion="Northern Europe",
        independent=True,
        capital_name="London",
        capital_latitude=51.5074,
        capital_longitude=-0.1278,
    )


@pytest.fixture
def name_probability(country):
    return NameCountryProbability.objects.create(
        name="John",
        country=country,
        probability=0.9,
        count_of_requests=1,
        last_accessed=timezone.now(),
    )


@pytest.mark.django_db
class TestNameProbabilityView:
    def test_get_without_name(self, client):
        url = reverse("name-probability")
        response = client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "Name parameter is required"}

    def test_get_existing_name_fresh(self, client, name_probability):
        url = reverse("name-probability")
        response = client.get(url, {"name": "John"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "John"
        assert data[0]["probability"] == 0.9
        assert data[0]["country_details"]["code"] == "US"
        assert data[0]["country_details"]["name"] == "United States"

    def test_get_existing_name_outdated(self, client, name_probability):
        # Устанавливаем last_accessed на 2 дня назад
        name_probability.last_accessed = timezone.now() - timedelta(days=2)
        name_probability.save()

        # Мокаем ответы от внешних API
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.nationalize.io/?name=John",
                json={"name": "John", "country": [{"country_id": "US", "probability": 0.95}]},
                status=200,
            )

            url = reverse("name-probability")
            response = client.get(url, {"name": "John"})

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "John"
            assert data[0]["probability"] == 0.95

    def test_get_existing_name_multiple_countries(self, client, country, uk_country):
        # Создаем записи для имени в разных странах
        NameCountryProbability.objects.create(
            name="James",
            country=country,
            probability=0.6,
            count_of_requests=1,
            last_accessed=timezone.now(),
        )
        NameCountryProbability.objects.create(
            name="James",
            country=uk_country,
            probability=0.4,
            count_of_requests=1,
            last_accessed=timezone.now(),
        )

        url = reverse("name-probability")
        response = client.get(url, {"name": "James"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Проверяем сортировку по вероятности
        assert data[0]["probability"] == 0.6
        assert data[0]["country_details"]["code"] == "US"
        assert data[1]["probability"] == 0.4
        assert data[1]["country_details"]["code"] == "GB"

    def test_get_name_with_special_chars(self, client):
        # Тестируем имя с специальными символами
        special_name = "O'Connor-Smith"
        encoded_name = urllib.parse.quote(special_name)

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://api.nationalize.io/?name={encoded_name}",
                json={"name": special_name, "country": [{"country_id": "IE", "probability": 0.8}]},
                status=200,
            )

            rsps.add(
                responses.GET,
                "https://restcountries.com/v3.1/alpha/IE",
                json=[
                    {
                        "name": {"common": "Ireland", "official": "Republic of Ireland"},
                        "region": "Europe",
                        "subregion": "Northern Europe",
                        "capital": ["Dublin"],
                        "capitalInfo": {"latlng": [53.3498, -6.2603]},
                    }
                ],
                status=200,
            )

            url = reverse("name-probability")
            response = client.get(url, {"name": special_name})
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data[0]["name"] == special_name

    def test_get_name_api_timeout(self, client):
        # Тестируем таймаут API
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.nationalize.io/?name=Timeout",
                body=requests.exceptions.Timeout(),
            )

            url = reverse("name-probability")
            response = client.get(url, {"name": "Timeout"})
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "error" in response.json()

    def test_get_name_invalid_json_response(self, client):
        # Тестируем некорректный JSON от API
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.nationalize.io/?name=Invalid",
                body="Invalid JSON",
                status=200,
            )

            url = reverse("name-probability")
            response = client.get(url, {"name": "Invalid"})
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "error" in response.json()

    def test_get_name_empty(self, client):
        # Тестируем пустое имя
        url = reverse("name-probability")
        response = client.get(url, {"name": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_get_name_too_long(self, client):
        # Тестируем слишком длинное имя
        long_name = "A" * 101  # Превышаем максимальную длину поля name
        url = reverse("name-probability")
        response = client.get(url, {"name": long_name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()


@pytest.mark.django_db
class TestPopularNamesView:
    def test_get_without_country(self, client):
        url = reverse("popular-names")
        response = client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "Country parameter is required"}

    def test_get_popular_names(self, client, name_probability):
        # Создаем дополнительные записи для тестирования
        for name, count in [("Alice", 5), ("Bob", 3), ("Charlie", 2)]:
            NameCountryProbability.objects.create(
                name=name,
                country=name_probability.country,
                probability=0.5,
                count_of_requests=count,
                last_accessed=timezone.now(),
            )

        url = reverse("popular-names")
        response = client.get(url, {"country": "US"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Проверяем, что имена отсортированы по количеству запросов
        assert len(data) == 4
        assert data[0]["name"] == "Alice"
        assert data[0]["total_requests"] == 5
        assert data[1]["name"] == "Bob"
        assert data[1]["total_requests"] == 3

    def test_get_nonexistent_country(self, client):
        url = reverse("popular-names")
        response = client.get(url, {"country": "XX"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "No data found for this country"}

    def test_get_popular_names_empty_country(self, client):
        # Тестируем пустой код страны
        url = reverse("popular-names")
        response = client.get(url, {"country": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_get_popular_names_invalid_country_code(self, client):
        # Тестируем некорректный формат кода страны
        url = reverse("popular-names")
        response = client.get(url, {"country": "USA"})  # Должно быть 2 символа
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_get_popular_names_zero_requests(self, client, country):
        # Создаем записи с нулевым количеством запросов
        NameCountryProbability.objects.create(
            name="Zero",
            country=country,
            probability=0.5,
            count_of_requests=0,
            last_accessed=timezone.now(),
        )

        url = reverse("popular-names")
        response = client.get(url, {"country": country.code})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "No data found for this country"}

    def test_get_popular_names_same_counts(self, client, country):
        # Создаем записи с одинаковым количеством запросов
        names = ["Anna", "Bob", "Charlie"]
        for name in names:
            NameCountryProbability.objects.create(
                name=name,
                country=country,
                probability=0.5,
                count_of_requests=5,
                last_accessed=timezone.now(),
            )

        url = reverse("popular-names")
        response = client.get(url, {"country": country.code})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 3
        assert all(item["total_requests"] == 5 for item in data)

        names_from_response = [item["name"] for item in data]
        assert names_from_response == sorted(names)
