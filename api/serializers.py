from datetime import timedelta

import requests
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from .models import Country, NameCountryProbability


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"
        help_texts = {
            "code": "Двухбуквенный код страны (ISO 3166-1 alpha-2)",
            "name": "Общепринятое название страны",
            "official_name": "Официальное название страны",
            "region": "Регион мира",
            "subregion": "Субрегион",
            "independent": "Является ли страна независимой",
            "capital_name": "Название столицы",
            "capital_latitude": "Широта столицы",
            "capital_longitude": "Долгота столицы",
            "flag_png_url": "URL флага в формате PNG",
            "flag_svg_url": "URL флага в формате SVG",
            "flag_alt": "Текстовое описание флага",
        }


class NameCountryProbabilitySerializer(serializers.ModelSerializer):
    country_details = CountrySerializer(
        source="country", read_only=True, help_text="Подробная информация о стране"
    )
    name = serializers.CharField(help_text="Анализируемое имя")
    probability = serializers.FloatField(
        help_text="Вероятность происхождения имени из данной страны"
    )
    count_of_requests = serializers.IntegerField(help_text="Количество запросов для данного имени")
    last_accessed = serializers.DateTimeField(help_text="Время последнего запроса")

    class Meta:
        model = NameCountryProbability
        fields = ["name", "probability", "count_of_requests", "last_accessed", "country_details"]

    @classmethod
    def get_or_fetch_probabilities(cls, name):
        one_day_ago = timezone.now() - timedelta(days=1)
        probabilities = NameCountryProbability.objects.filter(
            name=name, last_accessed__gte=one_day_ago
        ).select_related("country")

        if probabilities.exists():
            for prob in probabilities:
                prob.count_of_requests += 1
                prob.last_accessed = timezone.now()
                prob.save()
            return probabilities

        try:
            response = requests.get(f"https://api.nationalize.io/?name={name}")
            response.raise_for_status()
            nationalize_response = response.json()
        except (requests.RequestException, ValueError) as e:
            raise serializers.ValidationError(
                {"error": f"Error fetching data from external API: {str(e)}"}
            )

        if not nationalize_response.get("country"):
            return None

        results = []
        for country_data in nationalize_response["country"]:
            try:
                country = cls._get_or_create_country(country_data["country_id"])
                prob = cls._create_or_update_probability(name, country, country_data["probability"])
                results.append(prob)
            except Exception as e:
                raise serializers.ValidationError(
                    {"error": f"Error processing country data: {str(e)}"}
                )

        return results

    @staticmethod
    def _get_or_create_country(country_code):
        country = Country.objects.filter(code=country_code).first()

        if not country:
            try:
                fields = [
                    "name",
                    "capital",
                    "capitalInfo",
                    "region",
                    "subregion",
                    "independent",
                    "maps",
                    "flags",
                    "coatOfArms",
                    "borders",
                ]
                response = requests.get(
                    f"https://restcountries.com/v3.1/alpha/{country_code}"
                    f"?fields={','.join(fields)}"
                )
                response.raise_for_status()
                country_response = response.json()

                capital_coords = country_response.get("capitalInfo", {}).get("latlng", [None, None])
                capital_name = (
                    country_response.get("capital", [""])[0]
                    if country_response.get("capital")
                    else ""
                )

                country = Country.objects.create(
                    code=country_code,
                    name=country_response.get("name", {}).get("common", ""),
                    official_name=country_response.get("name", {}).get("official", ""),
                    region=country_response.get("region", ""),
                    subregion=country_response.get("subregion", ""),
                    independent=country_response.get("independent", False),
                    google_maps_url=country_response.get("maps", {}).get("googleMaps", ""),
                    openstreetmap_url=country_response.get("maps", {}).get("openStreetMaps", ""),
                    capital_name=capital_name,
                    capital_latitude=capital_coords[0] if capital_coords else None,
                    capital_longitude=capital_coords[1] if capital_coords else None,
                    flag_png_url=country_response.get("flags", {}).get("png", ""),
                    flag_svg_url=country_response.get("flags", {}).get("svg", ""),
                    flag_alt=country_response.get("flags", {}).get("alt", ""),
                    coat_of_arms_png_url=country_response.get("coatOfArms", {}).get("png", ""),
                    coat_of_arms_svg_url=country_response.get("coatOfArms", {}).get("svg", ""),
                )

                country.save()

                if country_response.get("borders"):
                    for border_code in country_response["borders"]:
                        try:
                            border_country = Country.objects.filter(code=border_code).first()
                            if not border_country:
                                border_country = (
                                    NameCountryProbabilitySerializer._get_or_create_country(
                                        border_code
                                    )
                                )
                            country.borders.add(border_country)
                        except Exception as e:
                            print(f"Error processing border country {border_code}: {str(e)}")
                            continue

            except requests.RequestException as e:
                raise serializers.ValidationError(f"Error fetching country data from API: {str(e)}")
            except (ValueError, KeyError, IndexError) as e:
                raise serializers.ValidationError(f"Error processing country data: {str(e)}")

        return country

    @staticmethod
    def _create_or_update_probability(name, country, probability):
        prob, created = NameCountryProbability.objects.get_or_create(
            name=name,
            country=country,
            defaults={
                "probability": probability,
                "count_of_requests": 1,
                "last_accessed": timezone.now(),
            },
        )

        if not created:
            prob.probability = probability
            prob.count_of_requests += 1
            prob.last_accessed = timezone.now()
            prob.save()

        return prob


class PopularNamesSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Имя")
    total_requests = serializers.IntegerField(help_text="Общее количество запросов для этого имени")

    @classmethod
    def get_popular_names(cls, country_code):
        return (
            NameCountryProbability.objects.filter(country__code=country_code)
            .values("name")
            .annotate(total_requests=Sum("count_of_requests"))
            .order_by("-total_requests")[:5]
        )
