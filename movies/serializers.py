from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Genre, Movie, Rating, Profile


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class MovieListSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    # Annotated by MovieListView queryset — None when no ratings yet
    avg_rating = serializers.FloatField(read_only=True, default=None)
    ratings_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Movie
        fields = ["id", "title", "poster_path", "release_date", "genres",
                  "avg_rating", "ratings_count"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True, default=None)
    ratings_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "overview", "release_date",
                  "poster_path", "genres", "avg_rating", "ratings_count"]


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ["id", "movie", "rating", "timestamp"]
        read_only_fields = ["timestamp"]

    def validate_rating(self, value):
        if not (0.5 <= value <= 5.0):
            raise serializers.ValidationError("Rating must be between 0.5 and 5.0")
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        rating, _ = Rating.objects.update_or_create(
            user=validated_data["user"],
            movie=validated_data["movie"],
            defaults={"rating": validated_data["rating"]},
        )
        return rating


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        Profile.objects.create(user=user)
        return user
