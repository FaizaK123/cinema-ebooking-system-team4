"""Test cases: the admin Add Movie form (validation + storage) and the movie catalog."""
import io
from pathlib import Path

from backend.infrastructure import config
from backend.tests.helpers import PNG_BYTES, ApiTestCase, make_customer


def movie_form(**overrides):
    form = {
        "title": "Test Movie One",
        "description": "A movie added by the automated tests.",
        "releaseDate": "2024-05-01",
        "duration": "125",
        "rating": "pg-13",
        "genres": ["Action", "sci-fi"],
        "poster": (io.BytesIO(PNG_BYTES), "poster.png"),
    }
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


class AddMovieTests(ApiTestCase):
    def post(self, client, **overrides):
        return client.post("/api/admin/movies", data=movie_form(**overrides), content_type="multipart/form-data")

    def test_only_admins_can_add_movies(self):
        self.assertEqual(self.post(self.client()).status_code, 401)
        make_customer("mover@example.com", "7065550301")
        customer = self.client()
        self.login(customer, "mover@example.com")
        self.assertEqual(self.post(customer).status_code, 403)

    def test_movie_is_stored_and_appears_in_the_user_portal(self):
        response = self.post(self.admin_client(), title="Stored Movie")
        self.assertEqual(response.status_code, 201, response.get_json())
        movie = response.get_json()["movie"]
        self.assertEqual(movie["runtime"], "2 hr 5 min")
        self.assertEqual(movie["rating"], "PG-13")
        self.assertEqual(movie["genre"], "Action, Sci-Fi")

        public = self.client().get(f"/api/movies/{movie['id']}").get_json()
        self.assertEqual(public["title"], "Stored Movie")
        self.assertEqual(public["releaseDate"], "2024-05-01")
        self.assertTrue(public["isCurrent"])            # released in the past
        self.assertEqual(public["showtimes"], {})        # none scheduled yet
        self.assertIn(public["id"], [m["id"] for m in self.client().get("/api/movies?title=Stored").get_json()])
        self.assertTrue((Path(config.POSTER_UPLOAD_DIR) / Path(public["poster"]).name).exists())

    def test_added_genres_work_with_the_genre_filter(self):
        self.post(self.admin_client(), title="Genre Movie", genres=["Western", "Sci-Fi"])
        for genre in ("Western", "Sci-Fi"):
            titles = [m["title"] for m in self.client().get(f"/api/movies?genre={genre}").get_json()]
            self.assertIn("Genre Movie", titles)
        genres = self.client().get("/api/genres").get_json()
        self.assertIn("Western", genres)
        self.assertEqual(len([g for g in genres if g.lower() == "sci-fi"]), 1)

    def test_future_release_date_is_coming_soon(self):
        response = self.post(self.admin_client(), title="Future Movie", releaseDate="2099-01-01")
        self.assertFalse(response.get_json()["movie"]["isCurrent"])

    def test_every_required_field_is_checked(self):
        client = self.admin_client()
        response = client.post("/api/admin/movies", data={}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.get_json()["errors"]),
            {"title", "description", "releaseDate", "duration", "rating", "genres", "poster"},
        )

    def test_invalid_values_are_rejected(self):
        client = self.admin_client()
        cases = [
            ({"title": "  "}, "title"),
            ({"title": "x" * 151}, "title"),
            ({"description": ""}, "description"),
            ({"releaseDate": "2024-13-45"}, "releaseDate"),
            ({"releaseDate": "05/01/2024"}, "releaseDate"),
            ({"duration": "0"}, "duration"),
            ({"duration": "-5"}, "duration"),
            ({"duration": "abc"}, "duration"),
            ({"duration": "601"}, "duration"),
            ({"rating": "XYZ"}, "rating"),
            ({"genres": ["Action3"]}, "genres"),
            ({"genres": []}, "genres"),
            ({"trailer": "http://example.com/video"}, "trailer"),
            ({"poster": (io.BytesIO(b"just some text"), "poster.png")}, "poster"),
            ({"poster": (io.BytesIO(PNG_BYTES + b"0" * (config.MAX_POSTER_BYTES + 1)), "big.png")}, "poster"),
        ]
        for override, field in cases:
            response = self.post(client, **{"title": "Invalid Movie", **override})
            self.assertIn(response.status_code, (400, 413), (override.keys(), response.get_json()))
            self.assertIn(field, response.get_json()["errors"], override.keys())
        titles = [m["title"] for m in self.client().get("/api/movies?title=Invalid").get_json()]
        self.assertEqual(titles, [])  # nothing invalid was stored

    def test_duplicate_title_is_rejected(self):
        client = self.admin_client()
        self.assertEqual(self.post(client, title="Duplicate Movie").status_code, 201)
        again = self.post(client, title="duplicate movie")
        self.assertEqual(again.status_code, 409)
        self.assertIn("title", again.get_json()["errors"])
        uploads = list(Path(config.POSTER_UPLOAD_DIR).glob("duplicate-movie-*"))
        self.assertEqual(len(uploads), 1)  # the rejected poster wasn't left behind

    def test_youtube_trailer_is_accepted(self):
        response = self.post(self.admin_client(), title="Trailer Movie", trailer="https://www.youtube.com/embed/abcDEF12345")
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()["movie"]["trailer"], "https://www.youtube.com/embed/abcDEF12345")
