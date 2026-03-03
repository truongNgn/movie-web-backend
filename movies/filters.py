import django_filters
from .models import Movie


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class MovieFilter(django_filters.FilterSet):
    genre = django_filters.CharFilter(field_name="genres__name", lookup_expr="iexact")
    genre_id = django_filters.NumberFilter(field_name="genres__id")
    year = django_filters.NumberFilter(field_name="release_date__year")
    ids = NumberInFilter(field_name="id", lookup_expr="in")

    class Meta:
        model = Movie
        fields = ["genre", "genre_id", "year", "ids"]
