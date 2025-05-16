from django.contrib import admin

from .models import Country, NameCountryProbability


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "region", "subregion"]
    list_filter = ["region", "subregion", "independent"]
    search_fields = ["code", "name", "official_name"]
    filter_horizontal = ["borders"]


@admin.register(NameCountryProbability)
class NameCountryProbabilityAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "probability", "count_of_requests", "last_accessed"]
    list_filter = ["country"]
    search_fields = ["name"]
    readonly_fields = ["count_of_requests", "last_accessed"]
