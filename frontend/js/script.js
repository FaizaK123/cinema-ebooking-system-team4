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

// /* Shared Movie Catalog - TEMPORARY */
// const movieCatalog = {
//     101: {
//         id: 101,
//         title: "Jaws",
//         poster: "images/moviePoster1.jpg",
//         rating: "PG",
//         runtime: "2 hr 4 min",
//         isCurrent: true,
//         showtimes: {
//             [nextTwoWeekDates[0].value]: ["6:30 PM", "8:45 PM"],
//             [nextTwoWeekDates[1].value]: ["2:15 PM"],
//             [nextTwoWeekDates[3].value]: ["7:00 PM"],
//             [nextTwoWeekDates[5].value]: ["4:30 PM"]
//         }
//     },
//     102: {
//         id: 102,
//         title: "The Silence of the Lambs",
//         poster: "images/moviePoster2.jpg",
//         rating: "R",
//         runtime: "1 hr 58 min",
//         isCurrent: true,
//         showtimes: {
//             [nextTwoWeekDates[0].value]: ["5:00 PM", "9:30 PM"],
//             [nextTwoWeekDates[1].value]: ["1:45 PM"],
//             [nextTwoWeekDates[4].value]: ["7:15 PM"]
//         }
//     },
//     103: {
//         id: 103,
//         title: "The Odyssey",
//         poster: "images/moviePoster3.jpg",
//         rating: "R",
//         runtime: "2 hr 19 min",
//         isCurrent: true,
//         showtimes: {
//             [nextTwoWeekDates[0].value]: ["1:00 PM"],
//             [nextTwoWeekDates[1].value]: ["4:45 PM"],
//             [nextTwoWeekDates[6].value]: ["6:00 PM"]
//         }
//     },
//     201: {
//         id: 201,
//         title: "Arrival",
//         poster: "images/moviePoster2.jpg",
//         releaseDate: "12/24/26",
//         isCurrent: false
//     },
//     202: {
//         id: 202,
//         title: "Dune",
//         poster: "images/moviePoster3.jpg",
//         releaseDate: "01/05/27",
//         isCurrent: false
//     }
// };

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

async function loadHomeMovies() {
    const params = new URLSearchParams();

    const searchInput = document.querySelector(".search-input");
    const title = searchInput ? searchInput.value.trim() : "";
    if (title) {
        params.append("title", title);
    }

    const checkedGenres = document.querySelectorAll(".homepage-filter-genre-section input:checked");
    checkedGenres.forEach(box => params.append("genre", box.value));

    const response = await fetch(`/api/movies?${params}`);
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
            loadHomeMovies();
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

    const button = card.querySelector(".movie-showtimes-button, .movie-trailer-button");
    if (button) {
        button.textContent = options.showShowtimes === false ? "Details" : "Showtimes";
        if (movie.id) {
            button.addEventListener("click", () => getShowtimes(movie.id));
        }
    }

    return card;
}

function getShowtimes(movieId) {
    window.location.href = `Movie_Page.html?id=${movieId}`;
}

/* - Filter Section Handling */
// const genres = [
//     "Comedy",
//     "Horror",
//     "Adventure",
//     "Rom-Com",
//     "Thriller",
//     "Sci-Fi"
// ];

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

async function loadGenreFilters() {
    try {
        const response = await fetch("/api/genres");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const genres = await response.json();
        renderFilterOptions(genres, ".homepage-filter-genre-section .filter-list", "genre");
    } catch (err) {
        console.error("Couldn't load genres:", err);
    }
}

loadGenreFilters();
renderFilterOptions(showtimeOptions, ".homepage-filter-date-section .filter-list", "showtime");

const genreSection = document.querySelector(".homepage-filter-genre-section");
if (genreSection) {
    genreSection.addEventListener("change", () => loadHomeMovies());
}

/* Movie_Page Handling */

/* - Showtimes Section Handling */
// const movieDatabase = movieCatalog;

function formatDateLabel(isoDate) {
    // parse as local time; new date("YYYY-MM-DD")
    const [year, month, day] = isoDate.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric"
    });
}

function renderMovieShowtimes(showtimesContainer, movie) {
    const dateSelect = showtimesContainer.querySelector("#showtime-date-select");
    const searchButton = showtimesContainer.querySelector("#showtime-search-button");
    const timesList = showtimesContainer.querySelector("#showtime-times-list");

    if (!dateSelect || !searchButton || !timesList) return;

    const dates = Object.keys(movie.showtimes || {}).sort();

    if (dates.length === 0){
        showtimesContainer.innerHTML =
            '<p class="moviepage-showtimes-empty-state">No showtimes available.</p>';
        return;
    }

    dateSelect.innerHTML = dates
        .map((date, i) => `
            <option value="${date}" ${i === 0 ? "selected" : ""}>
                ${formatDateLabel(date)}
            </option>
        `)
        .join("");



    // const initialDate = nextTwoWeekDates.find((option) => movie.showtimes[option.value]) || nextTwoWeekDates[0];

    // dateSelect.innerHTML = nextTwoWeekDates
    //     .map((option) => `
    //         <option value="${option.value}" ${option.value === initialDate.value ? "selected" : ""}>
    //             ${option.label}
    //         </option>
    //     `)
    //     .join("");

    function loadTimesForSelectedDate() {
        const selectedDate = dateSelect.value;
        const times = movie.showtimes[selectedDate] || [];

        timesList.innerHTML = times.length
            ? times.map((time) => `<button type="button" class="moviepage-showtime-button">${time}</button>`).join("")
            : '<p class="moviepage-showtimes-empty-state">No showtimes available for this date.</p>';

        timesList.querySelectorAll(".moviepage-showtime-button").forEach((button) => {
            button.addEventListener("click", () => {
                const params = new URLSearchParams({ id: movie.id, date: selectedDate, time: button.textContent });
                window.location.href = `Booking_Page.html?${params}`;
            });
        });
    }

    searchButton.addEventListener("click", loadTimesForSelectedDate);
    loadTimesForSelectedDate();
}

/* - Rendering Movie Handling */
async function renderMoviePage() {
    const title = document.getElementById("movie-title");
    const showtimesContainer = document.querySelector(".moviepage-showtimes-section");
    if (!title || !showtimesContainer) return;

    const movieId = new URLSearchParams(window.location.search).get("id")

    function showError(message) {
        title.textContent = message;
        showtimesContainer.innerHTML = "";
    }

    if (!movieId) {
        showError("Movie not found!");
        return;
    }



//     const params = new URLSearchParams(window.location.search);
//     const movieId = Number(params.get("id"));
//     const movie = movieDatabase[movieId];

//     if (!movie) {
//         title.textContent = "Movie not found";
//         showtimesContainer.innerHTML = "";
//         return;
//     }

    try {
        const response = await fetch(`/api/movies/${encodeURIComponent(movieId)}`);
        if (response.status === 404) {
            showError("Movie not found");
            return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const movie = await response.json();


        const runtime = document.getElementById("movie-runtime");
        const rating = document.getElementById("movie-rating");
        const poster = document.getElementById("moviepage-movie-poster");
        const desc = document.getElementById("movie-description");
        if (!runtime || !rating || !poster || !desc) return;

        title.textContent = movie.title;
        runtime.textContent = movie.runtime;
        rating.textContent = movie.rating;
        poster.src = movie.poster;
        poster.alt = movie.title;
        desc.textContent = movie.description;

        setUpTrailer(movie);
        renderMovieShowtimes(showtimesContainer, movie);
    } catch (err) {
        console.error(err);
        showError("Couldnt load this movie. Try again");
    }
}

/* - Trailer Handling */
function setUpTrailer(movie) {
    const trailerButton = document.getElementById("trailer-button");
    const trailerBox = document.getElementById("movie-trailer");
    if (!trailerButton || !trailerBox || !movie.trailer) return;

    trailerButton.addEventListener("click", () => {
        if (trailerBox.hidden) {
            trailerBox.innerHTML = `
                <iframe src="${movie.trailer}?autoplay=1" title="${movie.title} trailer"
                    allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen
                    referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
            trailerBox.hidden = false;
        } else {
            trailerBox.innerHTML = "";
            trailerBox.hidden = true;
        }
    });
}

if (document.getElementById("movie-title")) {
    renderMoviePage();
}

/* Booking_Page Handling */

async function renderBookingPage() {
    const title = document.getElementById("booking-movie-title");

    if (!title) return;

    const params = new URLSearchParams(window.location.search);

    const movieId = Number(params.get("id"));
    const selectedDate = params.get("date");
    const selectedTime = params.get("time");

    const response = await fetch("/api/movies");
    const movies = await response.json();

    const movie = movies.find(movie => movie.id === movieId);

    if (!movie) {
        title.textContent = "Movie not found";
        return;
    }

    title.textContent = movie.title;

    document.getElementById("booking-date").textContent =
        selectedDate || "Not selected";

    document.getElementById("booking-showtime").textContent =
        selectedTime || "Not selected";

    const seatLayout = document.getElementById("seat-layout");
    const rows = ["A", "B", "C", "D", "E"];

    rows.forEach(function (row) {
        for (let number = 1; number <= 8; number += 1) {
            const seat = document.createElement("button");

            seat.type = "button";
            seat.className = "booking-seat";
            seat.textContent = row + number;

            seat.addEventListener("click", function () {
                seat.classList.toggle("selected");
                updateBookingSummary();
            });

            seatLayout.appendChild(seat);
        }
    });

    const ticketInputs = [
        document.getElementById("adult-ticket"),
        document.getElementById("child-ticket"),
        document.getElementById("senior-ticket")
    ];

    ticketInputs.forEach(function (input) {
        input.addEventListener("input", updateBookingSummary);
    });

    updateBookingSummary();
}

function updateBookingSummary() {
    const adult =
        Number(document.getElementById("adult-ticket").value) || 0;

    const child =
        Number(document.getElementById("child-ticket").value) || 0;

    const senior =
        Number(document.getElementById("senior-ticket").value) || 0;

    const ticketCount =
        adult + child + senior;

    const total =
        (adult * 12) +
        (child * 8) +
        (senior * 9);

    const selectedSeatElements =
        document.querySelectorAll(".booking-seat.selected");

    const selectedSeats =
        Array.from(selectedSeatElements).map(function (seat) {
            return seat.textContent;
        });

    document.getElementById("ticket-count").textContent =
        ticketCount;

    document.getElementById("booking-total").textContent =
        total.toFixed(2);

    document.getElementById("selected-seats").textContent =
        selectedSeats.length > 0
            ? selectedSeats.join(", ")
            : "None";
}

if (document.getElementById("booking-movie-title")) {
    renderBookingPage();
}
