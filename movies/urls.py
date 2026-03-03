from django.urls import path
from .views import GenreListView, MovieListView, TrendingMoviesView, MovieDetailView, RatingCreateView

urlpatterns = [
    path("genres/", GenreListView.as_view(), name="genre-list"),
    path("movies/", MovieListView.as_view(), name="movie-list"),
    path("movies/trending/", TrendingMoviesView.as_view(), name="movie-trending"),
    path("movies/<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("ratings/", RatingCreateView.as_view(), name="rating-create"),
]
