from django.urls import path

from .views import NameProbabilityView, PopularNamesView

urlpatterns = [
    path("names/", NameProbabilityView.as_view(), name="name-probability"),
    path("popular-names/", PopularNamesView.as_view(), name="popular-names"),
]
