/* Home Button handling */
const homeBtn = document.getElementById("nav-bar-home-btn");
if (homeBtn) {
    homeBtn.addEventListener("click", function () {
        window.location.href = "Home_Page.html";
    });
}

/* Future Dates Handling */
function getNextTwoWeekDates() {
    const dates = [];
    const today = new Date();

    for (let i = 0; i < 14; i += 1) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);

        dates.push({
            value: date.toISOString().slice(0, 10),
            label: date.toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric"
            })
        });
    }

    return dates;
}
const nextTwoWeekDates = getNextTwoWeekDates();

/* Shared Movie Catalog - TEMPORARY */
const movieCatalog = {
    101: {
        id: 101,
        title: "Jaws",
        poster: "images/moviePoster1.jpg",
        rating: "PG",
        runtime: "2 hr 4 min",
        isCurrent: true,
        showtimes: {
            [nextTwoWeekDates[0].value]: ["6:30 PM", "8:45 PM"],
            [nextTwoWeekDates[1].value]: ["2:15 PM"],
            [nextTwoWeekDates[3].value]: ["7:00 PM"],
            [nextTwoWeekDates[5].value]: ["4:30 PM"]
        }
    },
    102: {
        id: 102,
        title: "The Silence of the Lambs",
        poster: "images/moviePoster2.jpg",
        rating: "R",
        runtime: "1 hr 58 min",
        isCurrent: true,
        showtimes: {
            [nextTwoWeekDates[0].value]: ["5:00 PM", "9:30 PM"],
            [nextTwoWeekDates[1].value]: ["1:45 PM"],
            [nextTwoWeekDates[4].value]: ["7:15 PM"]
        }
    },
    103: {
        id: 103,
        title: "The Odyssey",
        poster: "images/moviePoster3.jpg",
        rating: "R",
        runtime: "2 hr 19 min",
        isCurrent: true,
        showtimes: {
            [nextTwoWeekDates[0].value]: ["1:00 PM"],
            [nextTwoWeekDates[1].value]: ["4:45 PM"],
            [nextTwoWeekDates[6].value]: ["6:00 PM"]
        }
    },
    201: {
        id: 201,
        title: "Arrival",
        poster: "images/moviePoster2.jpg",
        releaseDate: "12/24/26",
        isCurrent: false
    },
    202: {
        id: 202,
        title: "Dune",
        poster: "images/moviePoster3.jpg",
        releaseDate: "01/05/27",
        isCurrent: false
    }
};

/* Home_Page Handling */

/* - Movie Poster Section Handling */
const cardTemplates = {};
function renderMovieSection(movieCond, movies, showtimes = {}) {
    const container = document.querySelector(movieCond);
    if (container && !cardTemplates[movieCond]) {
        cardTemplates[movieCond] = container.querySelector(".movie-card");
    }
    const template = cardTemplates[movieCond];
    if (!container || !template) return;

    container.innerHTML = "";

    if (movies.length === 0) {
        container.innerHTML = '<p class="no-movies-message">No movies found.</p>';
        return;
    }

    movies.forEach(movie => {
        container.appendChild(createMovieCard(movie, template, showtimes));
    });
}

async function loadHomeMovies(title = "") {
    const response = await fetch(`/api/movies?title=${encodeURIComponent(title)}`);
    const movies = await response.json();

    const currentMovies = movies.filter(movie => movie.isCurrent);
    const upcomingMovies = movies.filter(movie => !movie.isCurrent);

    renderMovieSection(".homepage-posters-section.current", currentMovies, {showShowtimes: true});
    renderMovieSection(".homepage-posters-section.upcoming", upcomingMovies, {showShowtimes: false});
}

loadHomeMovies()

const searchInput = document.querySelector(".search-input");
if (searchInput) {
    searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            loadHomeMovies(searchInput.value.trim());
        }
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

function getShowtimes(movieId) {
    window.location.href = `Movie_Page.html?id=${movieId}`;
}

/* - Filter Section Handling */
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

/* - Showtimes Section Handling */
const movieDatabase = movieCatalog;

function renderMovieShowtimes(showtimesContainer, movie) {
    const dateSelect = showtimesContainer.querySelector("#showtime-date-select");
    const searchButton = showtimesContainer.querySelector("#showtime-search-button");
    const timesList = showtimesContainer.querySelector("#showtime-times-list");

    if (!dateSelect || !searchButton || !timesList) return;

    const initialDate = nextTwoWeekDates.find((option) => movie.showtimes[option.value]) || nextTwoWeekDates[0];

    dateSelect.innerHTML = nextTwoWeekDates
        .map((option) => `
            <option value="${option.value}" ${option.value === initialDate.value ? "selected" : ""}>
                ${option.label}
            </option>
        `)
        .join("");

    function loadTimesForSelectedDate() {
        const selectedDate = dateSelect.value;
        const times = movie.showtimes[selectedDate] || [];

        timesList.innerHTML = times.length
            ? times.map((time) => `<button type="button" class="moviepage-showtime-button">${time}</button>`).join("")
            : '<p class="moviepage-showtimes-empty-state">No showtimes available for this date.</p>';
    }

    searchButton.addEventListener("click", loadTimesForSelectedDate);
    loadTimesForSelectedDate();
}

/* - Rendering Movie Handling */
function renderMoviePage() {
    const title = document.getElementById("movie-title");
    const showtimesContainer = document.querySelector(".moviepage-showtimes-section");
    if (!title || !showtimesContainer) return;

    const params = new URLSearchParams(window.location.search);
    const movieId = Number(params.get("id"));
    const movie = movieDatabase[movieId];

    if (!movie) {
        title.textContent = "Movie not found";
        showtimesContainer.innerHTML = "";
        return;
    }

    const runtime = document.getElementById("movie-runtime");
    const rating = document.getElementById("movie-rating");
    const poster = document.getElementById("moviepage-movie-poster");
    if (!runtime || !rating || !poster) return;

    title.textContent = movie.title;
    runtime.textContent = movie.runtime;
    rating.textContent = movie.rating;
    poster.src = movie.poster;

    renderMovieShowtimes(showtimesContainer, movie);
}

if (document.getElementById("movie-title")) {
    renderMoviePage();
}