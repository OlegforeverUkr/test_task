from django.db import models


class Country(models.Model):
    code = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=500)
    region = models.CharField(max_length=100)
    subregion = models.CharField(max_length=100)
    independent = models.BooleanField(null=True)
    google_maps_url = models.URLField(max_length=500, null=True, blank=True)
    openstreetmap_url = models.URLField(max_length=500, null=True, blank=True)
    capital_name = models.CharField(max_length=100, null=True, blank=True)
    capital_latitude = models.FloatField(null=True, blank=True)
    capital_longitude = models.FloatField(null=True, blank=True)
    flag_png_url = models.URLField(max_length=500, null=True, blank=True)
    flag_svg_url = models.URLField(max_length=500, null=True, blank=True)
    flag_alt = models.CharField(max_length=1000, null=True, blank=True)
    coat_of_arms_png_url = models.URLField(max_length=500, null=True, blank=True)
    coat_of_arms_svg_url = models.URLField(max_length=500, null=True, blank=True)
    borders = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta:
        verbose_name_plural = "countries"

    def __str__(self):
        return f"{self.code} - {self.name}"


class NameCountryProbability(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    probability = models.FloatField()
    count_of_requests = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "name country probabilities"
        unique_together = ["name", "country"]

    def __str__(self):
        return f"{self.name} - {self.country.code} ({self.probability})"
