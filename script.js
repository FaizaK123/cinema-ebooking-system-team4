const homeBtn = document.getElementById("nav-bar-home-btn");
if (homeBtn) {
    homeBtn.addEventListener("click", function () {
        window.location.href = "Home_Page.html";
    });
}

/* Home_Page JS */
/* - Movie Poster Handling */
const currentMovies = [
    { title: "Jaws", poster: "images/moviePoster1.jpg", id: 101 },
    { title: "The Silence of the Lambs", poster: "images/moviePoster2.jpg", id: 102 },
    { title: "The Odyssey", poster: "images/moviePoster3.jpg", id: 103 }
];

const upcomingMovies = [
    { title: "Arrival", poster: "images/moviePoster2.jpg", releaseDate: "12/24/26" },
    { title: "Dune", poster: "images/moviePoster3.jpg", releaseDate: "01/05/27" }
];

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
    window.location.href = `Movie_Page.html?id=${movieId}`;
}

/* - Filter Handling */
const genres = [
    "Comedy",
    "Horror",
    "Adventure",
    "Rom-Com",
    "Thriller"
];

const showtimeOptions = [
    { label: "Today", value: "today" },
    { label: "Tomorrow", value: "tomorrow" },
    { label: "This Weekend", value: "weekend" },
    { label: "Next Week", value: "next-week" }
];

function renderFilterOptions(options, selector, groupName = "genre") {
    const container = document.querySelector(selector);
    if (!container) return;

    const template = container.querySelector(".filter-tag");
    if (!template) return;

    container.innerHTML = "";

    options.forEach((option) => {
        const item = template.cloneNode(true);
        const checkbox = item.querySelector("input[type='checkbox']");
        const label = item.querySelector("label");

        if (!checkbox || !label) return;

        const value = typeof option === "string" ? option : option.value;
        const text = typeof option === "string" ? option : option.label;
        const id = `${groupName}-${String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

        checkbox.id = id;
        checkbox.checked = false;
        checkbox.name = groupName;
        checkbox.value = value;

        label.setAttribute("for", id);
        label.textContent = text;

        container.appendChild(item);
    });
}

renderFilterOptions(genres, ".homepage-filter-genre-section .filter-list", "genre");
renderFilterOptions(showtimeOptions, ".homepage-filter-date-section .filter-list", "showtime");

/* Movie_Page Handling */
const movieDatabase = {
    101: {
        title: "Jaws",
        rating: "PG",
        runtime: "2 hr 4 min",
        showtimes: ["Today • 6:30 PM", "Today • 8:45 PM", "Tomorrow • 2:15 PM"]
    },
    102: {
        title: "The Silence of the Lambs",
        rating: "R",
        runtime: "1 hr 58 min",
        showtimes: ["Today • 5:00 PM", "Today • 9:30 PM", "Saturday • 7:15 PM"]
    },
    103: {
        title: "The Odyssey",
        genre: "R",
        runtime: "2 hr 19 min",
        showtimes: ["Today • 1:00 PM", "Tomorrow • 4:45 PM", "Sunday • 6:00 PM"]
    }
};

function renderMoviePage() {
    const title = document.getElementById("movie-title");
    const showtimesContainer = document.querySelector(".moviepage-showtimes-section");
    if (!title || !showtimesContainer) return;

    const params = new URLSearchParams(window.location.search);
    const movieId = Number(params.get("id"));
    const movie = movieDatabase[movieId];

    if (!movie) {
        title.textContent = "Movie not found";
        return;
    }

    const runtime = document.getElementById("movie-runtime");
    const rating = document.getElementById("movie-rating");
    if (!runtime || !rating) return;
    title.textContent = movie.title;
    runtime.textContent = movie.runtime;
    rating.textContent = movie.rating;
    showtimesContainer.innerHTML = `
        <h3 class="moviepage-showtimes-section-title">Showtimes</h3>
        <div class="showtimes-list">
            ${movie.showtimes.map((time) => `<button type="button" class="showtime-button">${time}</button>`).join("")}
        </div>
    `;
}

if (document.querySelector("#movie-title")) {
    renderMoviePage();
}