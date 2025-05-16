from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NameCountryProbabilitySerializer, PopularNamesSerializer


class NameProbabilityView(APIView):
    def get(self, request):
        name = request.query_params.get("name", "").strip()
        if not name:
            return Response(
                {"error": "Name parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if len(name) > 100:
            return Response({"error": "Name is too long"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            probabilities = NameCountryProbabilitySerializer.get_or_fetch_probabilities(name)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if probabilities is None:
            return Response(
                {"error": "No data found for this name"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = NameCountryProbabilitySerializer(probabilities, many=True)
        return Response(serializer.data)


class PopularNamesView(APIView):
    def get(self, request):
        country_code = request.query_params.get("country", "").strip().upper()
        if not country_code:
            return Response(
                {"error": "Country parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if len(country_code) != 2:
            return Response(
                {"error": "Country code must be 2 characters long"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            top_names = PopularNamesSerializer.get_popular_names(country_code)
            # Фильтруем записи с нулевым количеством запросов
            top_names = [name for name in top_names if name["total_requests"] > 0]

            if not top_names:
                return Response(
                    {"error": "No data found for this country"}, status=status.HTTP_404_NOT_FOUND
                )

            # Сортируем по количеству запросов (по убыванию) и по имени (по возрастанию)
            top_names.sort(key=lambda x: (-x["total_requests"], x["name"]))

            serializer = PopularNamesSerializer(top_names, many=True)
            return Response(serializer.data)

        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
