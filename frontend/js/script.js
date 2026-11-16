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

/* ---------------------------------------------------------------- Home_Page.html handling */
/* Home Button handling */
const homeBtn = document.getElementById("nav-bar-home-btn");
if (homeBtn) {
    homeBtn.addEventListener("click", function () {
        window.location.href = "/pages/public/Home_Page.html";
    });
}

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
    markFavoriteHearts();
}

/* Fill in the hearts of movies the logged-in customer already favorited */
async function markFavoriteHearts() {
    const ids = await CES.favoriteIds();
    document.querySelectorAll(".favorite-heart[data-movie-id]").forEach((heart) => {
        CES.setHeartState(heart, ids.has(Number(heart.dataset.movieId)));
    });
}

if (new URLSearchParams(window.location.search).get("loggedOut") === "1") {
    CES.toast("You have been logged out.");
}

loadHomeMovies()

window.addEventListener("pageshow", (event) => {
    if (event.persisted && document.querySelector(".homepage-posters-section")) {
        loadHomeMovies().catch((error) => console.error("Could not refresh movies:", error));
    }
});

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

    const heart = card.querySelector(".favorite-heart");
    if (heart && movie.id) {
        heart.dataset.movieId = movie.id;
        CES.setHeartState(heart, false);
        heart.addEventListener("click", async () => {
            const isFavorite = await CES.toggleFavorite(movie.id);
            if (isFavorite !== null) CES.setHeartState(heart, isFavorite);
        });
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
    window.location.href = `/pages/public/Movie_Page.html?id=${movieId}`;
}

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

/* ---------------------------------------------------------------- Movie_Page.html handling */
/* - Showtimes Section Handling */
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

    const showings = Array.isArray(movie.showings) ? movie.showings : [];
    const dates = [...new Set(showings.map((showing) => showing.date).filter(Boolean))].sort();

    if (dates.length === 0){
        showtimesContainer.innerHTML =
            '<p class="moviepage-showtimes-empty-state">No showtimes available.</p>';
        return;
    }

    dateSelect.replaceChildren();
    dates.forEach((date, index) => {
        const option = new Option(formatDateLabel(date), date);
        option.selected = index === 0;
        dateSelect.add(option);
    });

    function loadTimesForSelectedDate() {
        const selectedDate = dateSelect.value;
        const selectedShowings = showings.filter((showing) => showing.date === selectedDate);
        timesList.replaceChildren();

        if (selectedShowings.length === 0) {
            const empty = document.createElement("p");
            empty.className = "moviepage-showtimes-empty-state";
            empty.textContent = "No showtimes available for this date.";
            timesList.appendChild(empty);
            return;
        }

        selectedShowings.forEach((showing) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "moviepage-showtime-button";
            button.textContent = `${showing.timeLabel} · ${showing.showroom}`;
            button.setAttribute("aria-label", `Select ${showing.timeLabel} in ${showing.showroom}`);
            button.addEventListener("click", () => {
                const params = new URLSearchParams({
                    id: String(movie.id),
                    showId: String(showing.showId)
                });
                window.location.href = `/pages/public/Booking_Page.html?${params}`;
            });
            timesList.appendChild(button);
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
        setUpFavoriteButton(movie);
        renderMovieShowtimes(showtimesContainer, movie);
    } catch (err) {
        console.error(err);
        showError("Couldnt load this movie. Try again");
    }
}

/* - Favorite Button Handling */
async function setUpFavoriteButton(movie) {
    const favoriteButton = document.getElementById("favorite-button");
    if (!favoriteButton) return;

    const showState = (isFavorite) => {
        CES.setHeartState(favoriteButton, isFavorite);
        favoriteButton.lastChild.textContent = isFavorite ? " Favorited" : " Favorite";
    };
    const ids = await CES.favoriteIds();
    showState(ids.has(movie.id));

    favoriteButton.addEventListener("click", async () => {
        const isFavorite = await CES.toggleFavorite(movie.id);
        if (isFavorite !== null) showState(isFavorite);
    });
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

/* ---------------------------------------------------------------- Booking_Page.html handling */
async function renderBookingPage() {
    const title = document.getElementById("booking-movie-title");

    if (!title) return;

    const params = new URLSearchParams(window.location.search);
    const showId = Number(params.get("showId"));
    const continueButton = document.getElementById("proceed-to-checkout");
    const showtimeError = document.getElementById("booking-showtime-error");

    function showError(message) {
        showtimeError.textContent = message;
        showtimeError.hidden = false;
        continueButton.disabled = true;
    }

    if (!Number.isSafeInteger(showId) || showId <= 0) {
        showError("Select a showtime from the movie page to continue.");
        return;
    }

    try {
        const response = await fetch(`/api/shows/${showId}`);
        if (!response.ok) {
            showError("That showtime could not be found. Please choose another one.");
            return;
        }

        const data = await response.json();
        const show = data.show;
        title.textContent = data.movie.title;
        document.getElementById("booking-date").textContent = show.date;
        document.getElementById("booking-showtime").textContent = show.timeLabel;
        document.getElementById("booking-showroom").textContent = show.showroom;

        if (!data.bookable) {
            showError("This showtime is no longer available. Please choose another one.");
            return;
        }
        continueButton.disabled = false;
    } catch (error) {
        console.error("Could not load the selected showtime:", error);
        showError("Could not load the selected showtime. Please try again.");
        return;
    }

    const seatLayout = document.getElementById("seat-layout");
    const ticketInputs = [
        document.getElementById("adult-ticket"),
        document.getElementById("child-ticket"),
        document.getElementById("senior-ticket")
    ];
    const rows = ["A", "B", "C", "D", "E"];

    rows.forEach(function (row) {
        for (let number = 1; number <= 8; number += 1) {
            const seat = document.createElement("button");

            seat.type = "button";
            seat.className = "booking-seat";
            seat.textContent = row + number;

            seat.addEventListener("click", function () {
                if (!seat.classList.contains("selected")) {
                    const ticketCount = ticketInputs.reduce(
                        function (count, input) {
                            return count + (Number(input.value) || 0);
                        },
                        0
                    );
                    const selectedSeatCount =
                        seatLayout.querySelectorAll(".booking-seat.selected").length;

                    if (ticketCount === 0) {
                        alert("Select your tickets before choosing seats.");
                        return;
                    }

                    if (selectedSeatCount >= ticketCount) {
                        alert("You can select only one seat per ticket.");
                        return;
                    }
                }

                seat.classList.toggle("selected");
                updateBookingSummary();
            });

            seatLayout.appendChild(seat);
        }
    });

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
