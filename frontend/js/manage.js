/* ---------------------------------------------------------------- Manage_Movies.html handling */
const addMovieButton = document.getElementById("add-movie-btn");
const addMovieForm = document.getElementById("add-movie-form");
const moviePosterInput = document.getElementById("movie-poster");
if (addMovieButton && addMovieForm) {
    addMovieButton.addEventListener("click", () => {
        addMovieForm.classList.remove("hidden");
    });

    const moviesList = document.getElementById("movies-list");
    const movieTitleInput = document.getElementById("movie-title");
    const movieDescriptionInput = document.getElementById("movie-description");
    const movieReleaseDateInput = document.getElementById("movie-release-date");
    const movieDurationInput = document.getElementById("movie-duration");
    const movieRatingInput = document.getElementById("movie-rating");
    const movieGenres = document.getElementById("movie-genres");
    const moviePosterPrompt = document.getElementById("movie-poster-prompt");
    const moviePosterSelected = document.getElementById("movie-poster-selected");
    const moviePosterFilename = document.getElementById("movie-poster-filename");
    const moviePosterStatus = document.getElementById("movie-poster-status");

    if (
        moviesList && movieTitleInput && movieDescriptionInput && movieReleaseDateInput &&
        movieDurationInput && movieRatingInput && movieGenres && moviePosterInput &&
        moviePosterPrompt && moviePosterSelected && moviePosterFilename && moviePosterStatus
    ) {
        addMovieForm.addEventListener("submit", (event) => {
            event.preventDefault();

            const posterFile = moviePosterInput.files[0];
            if (!posterFile) return;

            const card = document.createElement("article");
            card.className = "manage-movie-card";

            const poster = document.createElement("img");
            poster.className = "manage-movie-card-poster";
            poster.src = URL.createObjectURL(posterFile);
            poster.alt = `${movieTitleInput.value.trim()} poster`;

            const details = document.createElement("div");
            details.className = "manage-movie-card-details";

            const title = document.createElement("h2");
            title.textContent = movieTitleInput.value.trim();

            const info = document.createElement("p");
            info.textContent = `${movieReleaseDateInput.value} · ${movieDurationInput.value} min · ${movieRatingInput.value.toUpperCase()}`;

            const description = document.createElement("p");
            description.textContent = movieDescriptionInput.value.trim();

            const genres = document.createElement("div");
            genres.className = "manage-movie-card-genres";
            Array.from(movieGenres.children).forEach((genreTag) => {
                const genre = document.createElement("span");
                genre.className = "manage-movie-card-genre";
                genre.textContent = genreTag.dataset.genre;
                genres.appendChild(genre);
            });

            details.append(title, info, description, genres);
            card.append(poster, details);
            moviesList.prepend(card);

            addMovieForm.reset();
            movieGenres.replaceChildren();
            moviePosterPrompt.classList.remove("hidden");
            moviePosterSelected.classList.add("hidden");
            moviePosterFilename.textContent = "";
            moviePosterStatus.textContent = "";
            moviePosterStatus.classList.remove("is-error");
            addMovieForm.classList.add("hidden");
        });
    }
}

const movieGenreInput = document.getElementById("movie-genre");
const movieGenres = document.getElementById("movie-genres");
if (movieGenreInput && movieGenres) {
    movieGenreInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();

        const genre = movieGenreInput.value.trim();
        if (!genre) return;

        const alreadyAdded = Array.from(movieGenres.children).some((tag) =>
            tag.dataset.genre.toLowerCase() === genre.toLowerCase()
        );
        if (alreadyAdded) {
            movieGenreInput.value = "";
            return;
        }

        const tag = document.createElement("span");
        tag.className = "add-movie-form-genre";
        tag.dataset.genre = genre;
        tag.setAttribute("role", "listitem");

        const label = document.createElement("span");
        label.textContent = genre;

        const removeButton = document.createElement("button");
        removeButton.className = "add-movie-form-genre-remove";
        removeButton.type = "button";
        removeButton.textContent = "×";
        removeButton.setAttribute("aria-label", `Remove ${genre} genre`);
        removeButton.addEventListener("click", () => tag.remove());

        tag.append(label, removeButton);
        movieGenres.appendChild(tag);
        movieGenreInput.value = "";
    });
}

const moviePosterDropzone = document.getElementById("movie-poster-dropzone");
const moviePosterStatus = document.getElementById("movie-poster-status");
const moviePosterPrompt = document.getElementById("movie-poster-prompt");
const moviePosterSelected = document.getElementById("movie-poster-selected");
const moviePosterFilename = document.getElementById("movie-poster-filename");
const moviePosterRemoveButton = document.getElementById("movie-poster-remove-btn");
if (moviePosterInput && moviePosterDropzone && moviePosterStatus && moviePosterPrompt && moviePosterSelected && moviePosterFilename && moviePosterRemoveButton) {
    moviePosterDropzone.addEventListener("click", (event) => {
        if (event.target !== moviePosterInput && !moviePosterRemoveButton.contains(event.target)) {
            moviePosterInput.click();
        }
    });

    moviePosterDropzone.addEventListener("keydown", (event) => {
        if (event.target !== moviePosterDropzone || !["Enter", " "].includes(event.key)) return;
        event.preventDefault();
        moviePosterInput.click();
    });

    function showSelectedPoster() {
        const file = moviePosterInput.files[0];
        moviePosterStatus.classList.remove("is-error");

        if (!file) {
            moviePosterPrompt.classList.remove("hidden");
            moviePosterSelected.classList.add("hidden");
            moviePosterFilename.textContent = "";
            moviePosterStatus.textContent = "";
            return;
        }

        const hasAllowedExtension = /\.(jpe?g|png)$/i.test(file.name);
        const hasAllowedType = !file.type || ["image/jpeg", "image/png"].includes(file.type);
        if (!hasAllowedExtension || !hasAllowedType) {
            moviePosterInput.value = "";
            moviePosterPrompt.classList.remove("hidden");
            moviePosterSelected.classList.add("hidden");
            moviePosterFilename.textContent = "";
            moviePosterStatus.textContent = "Please choose a JPG or PNG image.";
            moviePosterStatus.classList.add("is-error");
            return;
        }

        moviePosterPrompt.classList.add("hidden");
        moviePosterFilename.textContent = file.name;
        moviePosterSelected.classList.remove("hidden");
        moviePosterStatus.textContent = "";
    }

    moviePosterInput.addEventListener("change", showSelectedPoster);
    moviePosterRemoveButton.addEventListener("click", () => {
        moviePosterInput.value = "";
        showSelectedPoster();
    });

    moviePosterDropzone.addEventListener("dragover", (event) => {
        event.preventDefault();
        moviePosterDropzone.classList.add("is-dragging");
    });

    moviePosterDropzone.addEventListener("dragleave", (event) => {
        if (!moviePosterDropzone.contains(event.relatedTarget)) {
            moviePosterDropzone.classList.remove("is-dragging");
        }
    });

    moviePosterDropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        moviePosterDropzone.classList.remove("is-dragging");

        const files = event.dataTransfer.files;
        if (!files.length) return;

        moviePosterInput.files = files;
        showSelectedPoster();
    });
}

/* ---------------------------------------------------------------- Manage_Showtimes.html handling */
const showtimeForm = document.getElementById("showtime-form");
if (showtimeForm) {
    const showtimeMovie = document.getElementById("showtime-movie");
    const showtimeDate = document.getElementById("showtime-date");
    const showtimeTime = document.getElementById("showtime-time");
    const showtimeShowroom = document.getElementById("showtime-showroom");
    const showtimeSubmit = document.getElementById("showtime-submit");
    const showtimeMessage = document.getElementById("showtime-form-message");
    const scheduledShowtimesList = document.getElementById("scheduled-showtimes-list");
    const scheduledShowtimesEmpty = document.getElementById("scheduled-showtimes-empty");

    function setShowtimeMessage(message, isError = false) {
        showtimeMessage.textContent = message;
        showtimeMessage.classList.toggle("is-error", isError);
    }

    function createShowtimeDetail(label, value) {
        const detail = document.createElement("span");
        detail.className = "scheduled-showtime-detail";

        const heading = document.createElement("strong");
        heading.textContent = label;
        const text = document.createElement("span");
        text.textContent = value;
        detail.append(heading, text);
        return detail;
    }

    async function loadShowtimeMovies() {
        try {
            const response = await fetch("/api/movies");
            if (!response.ok) throw new Error(`Movie list request failed (HTTP ${response.status}).`);

            const movies = await response.json();
            if (!Array.isArray(movies)) throw new Error("The movie list response was not a list.");

            showtimeMovie.replaceChildren(new Option("Select a movie", ""));
            movies.forEach((movie) => {
                if (!movie || typeof movie.title !== "string" || !movie.title.trim()) return;

                const option = new Option(movie.title, String(movie.id ?? movie.title));
                option.dataset.title = movie.title;
                showtimeMovie.add(option);
            });

            const hasMovies = showtimeMovie.options.length > 1;
            showtimeSubmit.disabled = !hasMovies;
            if (!hasMovies) {
                setShowtimeMessage("There are no movies available to schedule.");
            }
        } catch (error) {
            console.error("Could not load movies for showtime scheduling:", error);
            showtimeMovie.replaceChildren(new Option("Movies could not be loaded", ""));
            showtimeSubmit.disabled = true;
            setShowtimeMessage("Could not load movies. Please try again later.", true);
        }
    }

    const today = new Date();
    showtimeDate.min = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    showtimeForm.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!showtimeForm.reportValidity()) return;

        const selectedMovie = showtimeMovie.selectedOptions[0];
        const showroom = showtimeShowroom.value.trim();
        const showtimeAlreadyScheduled = Array.from(
            scheduledShowtimesList.querySelectorAll(".scheduled-showtime-card")
        ).some((card) =>
            card.dataset.date === showtimeDate.value &&
            card.dataset.time === showtimeTime.value &&
            card.dataset.showroom === showroom.toLowerCase()
        );

        if (showtimeAlreadyScheduled) {
            setShowtimeMessage(
                `A showtime is already scheduled in ${showroom} at this date and time. Choose another time or screen.`,
                true
            );
            return;
        }

        const selectedDate = new Date(`${showtimeDate.value}T00:00:00`);
        const dateLabel = selectedDate.toLocaleDateString(undefined, {
            year: "numeric",
            month: "long",
            day: "numeric"
        });
        const timeLabel = new Date(`2000-01-01T${showtimeTime.value}`).toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit"
        });

        const card = document.createElement("article");
        card.className = "scheduled-showtime-card";
        card.dataset.date = showtimeDate.value;
        card.dataset.time = showtimeTime.value;
        card.dataset.showroom = showroom.toLowerCase();
        card.append(
            createShowtimeDetail("Movie", selectedMovie.dataset.title || selectedMovie.textContent),
            createShowtimeDetail("Date", dateLabel),
            createShowtimeDetail("Time", timeLabel),
            createShowtimeDetail("Showroom", showroom)
        );

        scheduledShowtimesEmpty?.remove();
        scheduledShowtimesList.prepend(card);
        showtimeDate.value = "";
        showtimeTime.value = "";
        showtimeShowroom.value = "";
        setShowtimeMessage("Showtime added to this page.");
    });

    loadShowtimeMovies();
}
