from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from .serializers import NameCountryProbabilitySerializer, PopularNamesSerializer

name_probability_schema = extend_schema(
    summary="Получить вероятность происхождения имени",
    description="Возвращает список стран с вероятностями происхождения для заданного имени",
    parameters=[
        OpenApiParameter(
            name="name",
            description="Имя для анализа",
            required=True,
            type=str,
            examples=[
                OpenApiExample(
                    "Пример",
                    value="Ivan",
                    description="Имя должно содержать только буквы и быть не длиннее 100 символов",
                )
            ],
        )
    ],
    responses={
        200: NameCountryProbabilitySerializer(many=True),
        400: OpenApiExample("Ошибка валидации", value={"error": "Name parameter is required"}),
        404: OpenApiExample("Данные не найдены", value={"error": "No data found for this name"}),
        500: OpenApiExample("Внутренняя ошибка", value={"error": "Internal server error"}),
    },
)

popular_names_schema = extend_schema(
    summary="Получить популярные имена для страны",
    description="Возвращает топ-5 самых часто запрашиваемых имен для указанной страны",
    parameters=[
        OpenApiParameter(
            name="country",
            description="Двухбуквенный код страны (ISO 3166-1 alpha-2)",
            required=True,
            type=str,
            examples=[
                OpenApiExample(
                    "Пример", value="US", description="Код страны должен состоять из 2 букв"
                )
            ],
        )
    ],
    responses={
        200: PopularNamesSerializer(many=True),
        400: OpenApiExample("Ошибка валидации", value={"error": "Country parameter is required"}),
        404: OpenApiExample("Данные не найдены", value={"error": "No data found for this country"}),
        500: OpenApiExample("Внутренняя ошибка", value={"error": "Internal server error"}),
    },
)
