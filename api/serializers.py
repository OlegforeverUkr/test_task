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


class NameCountryProbabilitySerializer(serializers.ModelSerializer):
    country_details = CountrySerializer(source="country", read_only=True)

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
            country_response = requests.get(
                f"https://restcountries.com/v3.1/alpha/{country_code}"
            ).json()[0]

            capital_coords = country_response.get("capitalInfo", {}).get("latlng", [None, None])

            country = Country.objects.create(
                code=country_code,
                name=country_response["name"]["common"],
                official_name=country_response["name"]["official"],
                region=country_response.get("region", ""),
                subregion=country_response.get("subregion", ""),
                independent=country_response.get("independent"),
                google_maps_url=country_response.get("maps", {}).get("googleMaps"),
                openstreetmap_url=country_response.get("maps", {}).get("openStreetMaps"),
                capital_name=country_response.get("capital", [None])[0],
                capital_latitude=capital_coords[0],
                capital_longitude=capital_coords[1],
                flag_png_url=country_response.get("flags", {}).get("png"),
                flag_svg_url=country_response.get("flags", {}).get("svg"),
                flag_alt=country_response.get("flags", {}).get("alt"),
                coat_of_arms_png_url=country_response.get("coatOfArms", {}).get("png"),
                coat_of_arms_svg_url=country_response.get("coatOfArms", {}).get("svg"),
            )

            if country_response.get("borders"):
                border_countries = Country.objects.filter(code__in=country_response["borders"])
                country.borders.add(*border_countries)

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
    name = serializers.CharField()
    total_requests = serializers.IntegerField()

    @classmethod
    def get_popular_names(cls, country_code):
        return (
            NameCountryProbability.objects.filter(country__code=country_code)
            .values("name")
            .annotate(total_requests=Sum("count_of_requests"))
            .order_by("-total_requests")[:5]
        )
