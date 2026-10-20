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

/* Login_Page Handling */

/* forgot password handling */
const forgotPasswordForm = document.getElementById("forgot-password-form");
function showForgotPasswordError() {
    const errorMessage = document.getElementById("forgot-password-error");
    if (errorMessage) {
        errorMessage.hidden = false;
    }
}

if (forgotPasswordForm) {
    const errorMessage = document.getElementById("forgot-password-error");

    forgotPasswordForm.addEventListener("submit", function (event) {
        event.preventDefault();
        errorMessage.hidden = true;
        sessionStorage.setItem("passwordResetEmail", document.getElementById("fp-email").value.trim());
        sessionStorage.setItem("passwordResetApproved", "true");
        window.location.href = "Forgot_Password.html";
    });
}

const resetPasswordForm = document.getElementById("reset-password-form");
if (resetPasswordForm) {
    if (sessionStorage.getItem("passwordResetApproved") !== "true") {
        window.location.replace("Forgot_Password_Request.html");
    } else {
        const newPassword = document.getElementById("new-password");
        const confirmPassword = document.getElementById("confirm-password");
        const errorMessage = document.getElementById("reset-password-error");
        const successMessage = document.getElementById("reset-password-success");

        resetPasswordForm.addEventListener("submit", function (event) {
            event.preventDefault();
            errorMessage.hidden = true;
            successMessage.hidden = true;

            if (newPassword.value !== confirmPassword.value) {
                errorMessage.textContent = "The passwords do not match. Please try again.";
                errorMessage.hidden = false;
                confirmPassword.focus();
                return;
            }

            sessionStorage.removeItem("passwordResetApproved");
            sessionStorage.removeItem("passwordResetEmail");
            resetPasswordForm.querySelectorAll("input").forEach(function (input) {
                input.disabled = true;
            });
            resetPasswordForm.querySelector("button[type='submit']").disabled = true;
            successMessage.hidden = false;
        });
    }
}

/* Signup_Page Handling */ 

/* show password handling */
const passwordInput = document.getElementById("password");
const passwordToggle = document.getElementById("toggle-password");
if (passwordInput && passwordToggle) {
    passwordToggle.addEventListener("click", function () {
        const isVisible = passwordInput.type === "text";
        passwordInput.type = isVisible ? "password" : "text";
        passwordToggle.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
        passwordToggle.setAttribute("aria-pressed", String(!isVisible));
        passwordToggle.querySelector("i").classList.toggle("fa-eye", isVisible);
        passwordToggle.querySelector("i").classList.toggle("fa-eye-slash", !isVisible);
    });
}

const signupForm = document.getElementById("signup-form");
const signupDraftKey = "cinemaSignupDraft";

function readSignupDraft() {
    const savedDraft = sessionStorage.getItem(signupDraftKey);
    return savedDraft ? JSON.parse(savedDraft) : {};
}

function showSignupMessage(message, isError) {
    const messageElement = document.getElementById("signup-form-message");
    if (messageElement) {
        messageElement.textContent = message;
        messageElement.classList.toggle("error", isError);
        messageElement.hidden = false;
    }
}

/* address and payment summary handling */

function updateAddressSummary(address) {
    const summary = document.getElementById("signup-address-summary");
    const addressText = document.getElementById("signup-address-text");
    if (!summary || !addressText || !address) return;

    addressText.textContent = [
        address.street,
        `${address.city}, ${address.state} ${address.zip}`
    ].join(", ");
    summary.hidden = false;
    document.getElementById("address").textContent = "Edit Address";
}

function updatePaymentSummary(payment) {
    const summary = document.getElementById("signup-payment-summary");
    const paymentList = document.getElementById("signup-payment-list");
    const addPaymentButton = document.getElementById("payment");
    if (!summary || !paymentList) return;

    const payments = Array.isArray(payment) ? payment : payment ? [payment] : [];

    paymentList.replaceChildren();
    payments.forEach(function (card, index) {
        const listItem = document.createElement("li");
        listItem.textContent = `Card ${index + 1}: ending in ${card.last4}, expires ${card.expiration}`;
        paymentList.appendChild(listItem);
    });
    summary.hidden = payments.length === 0;

    if (addPaymentButton) {
        const cardLimitReached = payments.length >= 3;
        addPaymentButton.disabled = cardLimitReached;
        addPaymentButton.textContent = cardLimitReached
            ? "Maximum of 3 cards added"
            : payments.length > 0 ? "Add Another Payment Card" : "Add Payment Info";
    }
}

if (signupForm) {
    let signupDraft = {};
    try {
        signupDraft = readSignupDraft();
        signupForm.querySelectorAll("[name]").forEach(function (input) {
            if (signupDraft[input.name] !== undefined) {
                input.value = signupDraft[input.name];
            }
        });
        updateAddressSummary(signupDraft.address);
        updatePaymentSummary(signupDraft.payment);
    } catch (error) {
        console.error("Could not restore signup information:", error);
        showSignupMessage("Saved signup information could not be restored.", true);
    }

    signupForm.addEventListener("input", function () {
        try {
            signupDraft = readSignupDraft();
            signupForm.querySelectorAll("[name]").forEach(function (input) {
                signupDraft[input.name] = input.value;
            });
            sessionStorage.setItem(signupDraftKey, JSON.stringify(signupDraft));
        } catch (error) {
            console.error("Could not save signup information:", error);
            showSignupMessage("Signup information could not be saved in this browser.", true);
        }
    });

    const addAddressButton = document.getElementById("address");
    const editAddressButton = document.getElementById("edit-address");
    [addAddressButton, editAddressButton].forEach(function (button) {
        if (button) {
            button.addEventListener("click", function () {
                try {
                    signupDraft = readSignupDraft();
                    signupForm.querySelectorAll("[name]").forEach(function (input) {
                        signupDraft[input.name] = input.value;
                    });
                    sessionStorage.setItem(signupDraftKey, JSON.stringify(signupDraft));
                    window.location.href = "Address_Info_Page.html";
                } catch (error) {
                    console.error("Could not save signup information:", error);
                    showSignupMessage("Could not save your information before opening the address form.", true);
                }
            });
        }
    });

    signupForm.addEventListener("submit", function (event) {
        event.preventDefault();
        try {
            signupDraft = readSignupDraft();
            signupForm.querySelectorAll("[name]").forEach(function (input) {
                signupDraft[input.name] = input.value;
            });

            const demoAccount = {
                name: signupDraft.name,
                email: signupDraft.email,
                phone: signupDraft.phone,
                password: signupDraft.password,
                address: signupDraft.address || null,
                payment: Array.isArray(signupDraft.payment) ? signupDraft.payment : []
            };
            localStorage.setItem("cinemaDemoAccount", JSON.stringify(demoAccount));
            sessionStorage.removeItem(signupDraftKey);
            showSignupMessage("Demo account saved in this browser. Connect a backend before using real accounts.", false);
        } catch (error) {
            console.error("Could not save demo account:", error);
            showSignupMessage("The demo account could not be saved in this browser.", true);
        }
    });
}

const addressForm = document.getElementById("address-form");
if (addressForm) {
    const addressMessage = document.getElementById("address-form-message");
    try {
        const savedAddress = readSignupDraft().address;
        if (savedAddress) {
            ["street", "city", "state", "zip"].forEach(function (field) {
                document.getElementById(field).value = savedAddress[field] || "";
            });
        }
    } catch (error) {
        console.error("Could not restore address information:", error);
        addressMessage.textContent = "Saved address information could not be restored.";
        addressMessage.hidden = false;
    }

    addressForm.addEventListener("submit", function (event) {
        event.preventDefault();
        addressMessage.hidden = true;
        try {
            const signupDraft = readSignupDraft();
            signupDraft.address = {
                street: document.getElementById("street").value.trim(),
                city: document.getElementById("city").value.trim(),
                state: document.getElementById("state").value.trim(),
                zip: document.getElementById("zip").value.trim()
            };
            sessionStorage.setItem(signupDraftKey, JSON.stringify(signupDraft));
            window.location.href = "Signup_Page.html";
        } catch (error) {
            console.error("Could not save address information:", error);
            addressMessage.textContent = "The address could not be saved in this browser.";
            addressMessage.hidden = false;
        }
    });
}

const paymentButton = document.getElementById("payment");
if (paymentButton) {
    const editPaymentButton = document.getElementById("edit-payment");
    [paymentButton, editPaymentButton].forEach(function (button) {
        if (button) {
            button.addEventListener("click", function () {
                window.location.href = "Payment_Info_Page.html";
            });
        }
    });
}

const paymentForm = document.getElementById("payment-form");
if (paymentForm) {
    const message = document.getElementById("payment-form-message");
    const addCardButton = paymentForm.querySelector("button[type='submit']");
    let currentPayments = [];

    try {
        const savedPayments = readSignupDraft().payment;
        currentPayments = Array.isArray(savedPayments)
            ? savedPayments
            : savedPayments ? [savedPayments] : [];
    } catch (error) {
        console.error("Could not read saved payment cards:", error);
        message.textContent = "Saved payment information could not be read.";
        message.hidden = false;
        addCardButton.disabled = true;
    }

    if (currentPayments.length >= 3) {
        message.textContent = "You have reached the maximum of 3 payment cards.";
        message.hidden = false;
        addCardButton.disabled = true;
    }

    paymentForm.addEventListener("submit", function (event) {
        event.preventDefault();
        message.hidden = true;

        if (currentPayments.length >= 3) {
            message.textContent = "You can add up to 3 payment cards.";
            message.hidden = false;
            return;
        }

        const cardNumber = document.getElementById("card-num").value.replace(/\s/g, "");
        if (!/^\d{12,19}$/.test(cardNumber)) {
            message.textContent = "Enter a card number containing 12 to 19 digits.";
            message.hidden = false;
            document.getElementById("card-num").focus();
            return;
        }

        try {
            const signupDraft = readSignupDraft();
            const payments = Array.isArray(signupDraft.payment)
                ? signupDraft.payment
                : signupDraft.payment ? [signupDraft.payment] : [];
            payments.push({
                last4: cardNumber.slice(-4),
                expiration: document.getElementById("expire").value
            });
            signupDraft.payment = payments;
            sessionStorage.setItem(signupDraftKey, JSON.stringify(signupDraft));
            window.location.href = "Signup_Page.html";
        } catch (error) {
            console.error("Could not save payment summary:", error);
            message.textContent = "Payment information could not be saved in this browser.";
            message.hidden = false;
        }
    });
}