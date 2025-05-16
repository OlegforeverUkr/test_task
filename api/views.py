from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NameCountryProbabilitySerializer, PopularNamesSerializer


class NameProbabilityView(APIView):
    def get(self, request):
        name = request.query_params.get("name")
        if not name:
            return Response(
                {"error": "Name parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        probabilities = NameCountryProbabilitySerializer.get_or_fetch_probabilities(name)

        if probabilities is None:
            return Response(
                {"error": "No data found for this name"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = NameCountryProbabilitySerializer(probabilities, many=True)
        return Response(serializer.data)


class PopularNamesView(APIView):
    def get(self, request):
        country_code = request.query_params.get("country")
        if not country_code:
            return Response(
                {"error": "Country parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        top_names = PopularNamesSerializer.get_popular_names(country_code)

        if not top_names:
            return Response(
                {"error": "No data found for this country"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PopularNamesSerializer(top_names, many=True)
        return Response(serializer.data)
