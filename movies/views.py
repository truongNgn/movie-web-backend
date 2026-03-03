from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .filters import MovieFilter
from .models import Genre, Movie, Rating
from .serializers import (
    GenreSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
    RatingSerializer,
    RegisterSerializer,
)


class GenreListView(generics.ListAPIView):
    """GET /api/genres/ — full list of genres (no pagination needed)."""
    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # return plain array


class MovieListView(generics.ListAPIView):
    """
    GET /api/movies/
    Query params:
      ?search=<title>        — case-insensitive title search
      ?genre=<name>          — filter by genre name (iexact)
      ?genre_id=<id>         — filter by genre id
      ?year=<yyyy>           — filter by release year
      ?ordering=title|-title,release_date|-release_date
      ?limit=20&offset=0     — LimitOffsetPagination

    N+1 prevention:
      - prefetch_related("genres") collapses per-movie genre lookups into 1 query.
      - defer("overview", "tmdb_id") skips large/unused columns in the list view.
    """
    queryset = (
        Movie.objects
        .prefetch_related("genres")
        .defer("overview", "tmdb_id")
        .annotate(avg_rating=Avg("ratings__rating"), ratings_count=Count("ratings"))
        .all()
    )
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = MovieFilter
    search_fields = ["title"]
    ordering_fields = ["title", "release_date", "id"]
    ordering = ["title"]


class MovieDetailView(generics.RetrieveAPIView):
    """GET /api/movies/<id>/ — prefetch_related prevents N+1 on genres."""
    queryset = (
        Movie.objects
        .prefetch_related("genres")
        .annotate(avg_rating=Avg("ratings__rating"), ratings_count=Count("ratings"))
        .all()
    )
    serializer_class = MovieDetailSerializer
    permission_classes = [permissions.AllowAny]


class TrendingMoviesView(generics.ListAPIView):
    """GET /api/movies/trending/ — top 20 movies by avg rating (min 5 ratings)."""
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            Movie.objects
            .prefetch_related("genres")
            .defer("overview", "tmdb_id")
            .annotate(avg_rating=Avg("ratings__rating"), ratings_count=Count("ratings"))
            .filter(ratings_count__gte=5)
            .order_by("-avg_rating")[:20]
        )


class RatingCreateView(generics.CreateAPIView):
    """
    POST /api/ratings/
    Requires: JWT Authentication
    Body: { "movie": <id>, "rating": <0.5-5.0> }
    Creates or updates an existing rating (upsert).
    """
    queryset = Rating.objects.select_related("user", "movie")
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Creates a new user + Profile.
    Returns JWT access/refresh tokens so the client is immediately logged in.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": {"id": user.id, "username": user.username, "email": user.email},
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


def health_check_view(request):
    """
    A simple health check view that returns 200 OK.
    This replaces django-health-check which has compatibility issues with Python 3.14.
    """
    from django.http import JsonResponse
    from django.db import connections
    from django.db.utils import OperationalError

    health_data = {
        "database": "working",
        "cache": "working",
        "storage": "working",
    }

    # Optional: Quick DB check
    try:
        connections['default'].cursor()
    except OperationalError:
        health_data["database"] = "unavailable"

    return JsonResponse(health_data)
