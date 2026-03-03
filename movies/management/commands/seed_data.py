"""
Management command: seed MovieLens data into the database.

Usage:
    python manage.py seed_data                      # seed movies + ratings
    python manage.py seed_data --movies-only        # skip ratings
    python manage.py seed_data --ratings-limit 5000 # seed only first N ratings
    python manage.py seed_data --data-dir /custom/path

Data files expected (relative to manage.py by default):
    ml-latest-small-data/movies.csv   — movieId, title, genres (pipe-separated)
    ml-latest-small-data/ratings.csv  — userId, movieId, rating, timestamp
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from movies.models import Genre, Movie, Profile, Rating

logger = logging.getLogger("movies")

BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Seed MovieLens CSV data (movies + ratings) into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to the directory containing movies.csv and ratings.csv. "
                 "Defaults to <BASE_DIR>/ml-latest-small-data/",
        )
        parser.add_argument(
            "--movies-only",
            action="store_true",
            help="Seed only movies and genres, skip ratings.",
        )
        parser.add_argument(
            "--ratings-limit",
            type=int,
            default=None,
            help="Maximum number of rating rows to import (useful for quick testing).",
        )

    # ──────────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        # Resolve data directory
        if options["data_dir"]:
            data_dir = Path(options["data_dir"])
        else:
            # parents[0]=commands/ [1]=management/ [2]=movies/ [3]=backend/ [4]=movie-web (project root)
            data_dir = Path(__file__).resolve().parents[4] / "ml-latest-small-data"

        movies_csv = data_dir / "movies.csv"
        ratings_csv = data_dir / "ratings.csv"

        if not movies_csv.exists():
            raise CommandError(f"movies.csv not found at: {movies_csv}")

        self.stdout.write(self.style.MIGRATE_HEADING("=== Seeding MovieLens data ==="))

        self._seed_movies(movies_csv)

        if not options["movies_only"]:
            if not ratings_csv.exists():
                self.stdout.write(self.style.WARNING(f"ratings.csv not found at {ratings_csv}. Skipping ratings."))
            else:
                self._seed_ratings(ratings_csv, limit=options["ratings_limit"])

        self.stdout.write(self.style.SUCCESS("Done!"))

    # ──────────────────────────────────────────────────────────────────────
    def _seed_movies(self, csv_path: Path):
        self.stdout.write(f"Reading {csv_path} …")
        df = pd.read_csv(csv_path, dtype={"movieId": int, "title": str, "genres": str})
        df.dropna(subset=["movieId", "title"], inplace=True)

        # ── Step 1: collect & bulk-create all unique genres ────────────────
        all_genre_names: set[str] = set()
        for genres_str in df["genres"]:
            if genres_str and genres_str != "(no genres listed)":
                all_genre_names.update(g.strip() for g in genres_str.split("|") if g.strip())

        self.stdout.write(f"  Upserting {len(all_genre_names)} genres …")
        Genre.objects.bulk_create(
            [Genre(name=name) for name in all_genre_names],
            ignore_conflicts=True,
        )
        genre_map: dict[str, Genre] = {g.name: g for g in Genre.objects.all()}

        # ── Step 2: bulk-upsert movies ─────────────────────────────────────
        self.stdout.write(f"  Upserting {len(df)} movies …")
        movie_objs = [
            Movie(
                id=int(row["movieId"]),
                title=str(row["title"]).strip(),
            )
            for _, row in df.iterrows()
        ]
        Movie.objects.bulk_create(movie_objs, ignore_conflicts=True)

        # ── Step 3: set M2M genres via a through-table approach ────────────
        self.stdout.write("  Setting movie↔genre relationships …")
        movie_map: dict[int, Movie] = {m.id: m for m in Movie.objects.all()}

        # Clear existing M2M to avoid duplicates on re-seed
        Movie.genres.through.objects.all().delete()

        through_rows = []
        for _, row in df.iterrows():
            movie = movie_map.get(int(row["movieId"]))
            if not movie:
                continue
            genres_str = str(row["genres"])
            if genres_str and genres_str != "(no genres listed)":
                for gname in genres_str.split("|"):
                    gname = gname.strip()
                    genre = genre_map.get(gname)
                    if genre:
                        through_rows.append(
                            Movie.genres.through(movie_id=movie.id, genre_id=genre.id)
                        )

        Movie.genres.through.objects.bulk_create(through_rows, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {Movie.objects.count()} movies, {Genre.objects.count()} genres seeded."))

    # ──────────────────────────────────────────────────────────────────────
    def _seed_ratings(self, csv_path: Path, limit: int | None = None):
        self.stdout.write(f"Reading {csv_path} …")
        df = pd.read_csv(
            csv_path,
            dtype={"userId": int, "movieId": int, "rating": float, "timestamp": int},
            nrows=limit,
        )
        df.dropna(inplace=True)

        unique_user_ids: list[int] = sorted(df["userId"].unique().tolist())
        self.stdout.write(f"  Creating/fetching {len(unique_user_ids)} seed users …")

        # Create seed users (username = "seed_user_<userId>")
        existing_usernames = set(
            User.objects.filter(
                username__in=[f"seed_user_{uid}" for uid in unique_user_ids]
            ).values_list("username", flat=True)
        )
        new_users = [
            User(username=f"seed_user_{uid}", password="!")  # unusable password
            for uid in unique_user_ids
            if f"seed_user_{uid}" not in existing_usernames
        ]
        if new_users:
            User.objects.bulk_create(new_users, ignore_conflicts=True)
            # Create profiles for new users
            created_users = User.objects.filter(
                username__in=[u.username for u in new_users]
            )
            Profile.objects.bulk_create(
                [Profile(user=u) for u in created_users],
                ignore_conflicts=True,
            )

        user_map: dict[int, int] = {
            int(uname.replace("seed_user_", "")): uid
            for uname, uid in User.objects.filter(
                username__startswith="seed_user_"
            ).values_list("username", "id")
        }
        valid_movie_ids: set[int] = set(Movie.objects.values_list("id", flat=True))

        # ── Batch-insert ratings ───────────────────────────────────────────
        self.stdout.write(f"  Inserting {len(df)} ratings in batches of {BATCH_SIZE} …")
        total_inserted = 0

        with transaction.atomic():
            # Clear existing seed ratings to avoid duplicates
            Rating.objects.filter(user__username__startswith="seed_user_").delete()

            batch: list[Rating] = []
            for _, row in df.iterrows():
                uid = int(row["userId"])
                mid = int(row["movieId"])

                if uid not in user_map or mid not in valid_movie_ids:
                    continue

                batch.append(
                    Rating(
                        user_id=user_map[uid],
                        movie_id=mid,
                        rating=float(row["rating"]),
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    Rating.objects.bulk_create(batch, ignore_conflicts=True)
                    total_inserted += len(batch)
                    batch = []

            if batch:
                Rating.objects.bulk_create(batch, ignore_conflicts=True)
                total_inserted += len(batch)

        self.stdout.write(self.style.SUCCESS(f"  ✓ {total_inserted} ratings seeded."))
