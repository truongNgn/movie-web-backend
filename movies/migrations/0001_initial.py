import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Genre ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Genre",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
        ),
        # ── Movie ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Movie",
            fields=[
                ("id", models.IntegerField(primary_key=True, serialize=False)),
                ("tmdb_id", models.IntegerField(blank=True, null=True)),
                ("title", models.CharField(max_length=500)),
                ("overview", models.TextField(blank=True)),
                ("release_date", models.DateField(blank=True, null=True)),
                ("poster_path", models.CharField(blank=True, max_length=500)),
                ("genres", models.ManyToManyField(blank=True, related_name="movies", to="movies.genre")),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        # ── Rating ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.FloatField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "movie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ratings",
                        to="movies.movie",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ratings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "movie")},
            },
        ),
        # ── Profile ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("favorite_genres", models.ManyToManyField(blank=True, related_name="profiles", to="movies.genre")),
            ],
        ),
    ]
