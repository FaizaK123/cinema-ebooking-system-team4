const currentMovies = [
    { title: "Jaws", poster: "images/moviePoster1.jpg", id: 101 },
    { title: "The Silence of the Lambs", poster: "images/moviePoster2.jpg", id: 102 },
    { title: "The Odyssey", poster: "images/moviePoster3.jpg", id: 103 }
];

const upcomingMovies = [
    { title: "Arrival", poster: "images/moviePoster2.jpg", releaseDate: "12/24/26" },
    { title: "Dune", poster: "images/moviePoster3.jpg", releaseDate: "01/05/27" }
];

/* Movie Poster Handling */
function renderMovieSection(movieCond, movies, showtimes = {}) {
    const container = document.querySelector(movieCond);
    const template = container ? container.querySelector(".movie-card") : null;
    if (!container || !template) return;

    container.innerHTML = "";
    movies.forEach(movie => {
        container.appendChild(createMovieCard(movie, template, showtimes));
    });
}

function createMovieCard(movie, templateCard, options = {}) {
    const card = templateCard.cloneNode(true);

    const poster = card.querySelector(".movie-poster");
    if (poster) {
        poster.src = movie.poster;
        poster.alt = movie.title;
    }

    const title = card.querySelector(".movie-title");
    if (title) {
        title.textContent = movie.title;
    }

    const releaseDate = card.querySelector(".movie-release-date");
    if (releaseDate && movie.releaseDate) {
        releaseDate.textContent = movie.releaseDate;
    }

    const button = card.querySelector(".movie-showtimes-button");
    if (button) {
        if (options.showShowtimes === false) {
            button.remove();
        } else if (movie.id) {
            button.addEventListener("click", () => getShowtimes(movie.id));
        }
    }

    return card;
}

renderMovieSection(".homepage-posters-section.current", currentMovies, { showShowtimes: true });
renderMovieSection(".homepage-posters-section.upcoming", upcomingMovies, { showShowtimes: false });

function getShowtimes(movieId) {
    console.log(`Showing showtimes for movie ID: ${movieId}`);
}

/* Filter Handling */
const genres = [
    "Comedy",
    "Horror",
    "Adventure",
    "Rom-Com",
    "Thriller"
];

function renderGenreFilters(genres, selector) {
    const container = document.querySelector(selector);
    if (!container) return;

    const input = container.querySelector("input[type='checkbox']");
    const name = container.querySelector("label");
    if (!input || !name) return;

    container.innerHTML = "";
    genres.forEach((genre) => {
        const checkbox = input.cloneNode(true);
        const label = name.cloneNode(true);
        const id = `genre-${genre.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

        checkbox.id = id;
        checkbox.checked = false;
        checkbox.name = "genre";
        checkbox.value = genre;

        label.setAttribute("for", id);
        label.textContent = genre;

        container.appendChild(checkbox);
        container.appendChild(label);
    });
}

renderGenreFilters(genres, ".filter-list");
