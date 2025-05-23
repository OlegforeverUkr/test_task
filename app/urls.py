from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("api/documentation/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/documentation/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/documentation/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
