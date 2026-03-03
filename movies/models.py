from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    # movieId from MovieLens CSV (used as primary key)
    id = models.IntegerField(primary_key=True)
    tmdb_id = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=500)
    overview = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    poster_path = models.CharField(max_length=500, blank=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name="movies")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="ratings")
    rating = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "movie")

    def __str__(self):
        return f"{self.user.username} → {self.movie.title}: {self.rating}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    favorite_genres = models.ManyToManyField(Genre, blank=True, related_name="profiles")

    def __str__(self):
        return f"Profile({self.user.username})"
