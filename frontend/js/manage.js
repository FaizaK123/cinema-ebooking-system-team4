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

    function createMovieCard(movie) {
        const card = document.createElement("article");
        card.className = "manage-movie-card";

        const poster = document.createElement("img");
        poster.className = "manage-movie-card-poster";
        poster.src = movie.poster;
        poster.alt = `${movie.title} poster`;

        const details = document.createElement("div");
        details.className = "manage-movie-card-details";

        const title = document.createElement("h2");
        title.textContent = movie.title;

        const info = document.createElement("p");
        info.textContent = `${movie.releaseDate} · ${movie.runtime} · ${movie.rating}`;

        const description = document.createElement("p");
        description.textContent = movie.description;

        const genres = document.createElement("div");
        genres.className = "manage-movie-card-genres";
        String(movie.genre || "").split(",").map((genre) => genre.trim()).filter(Boolean).forEach((genreName) => {
            const genre = document.createElement("span");
            genre.className = "manage-movie-card-genre";
            genre.textContent = genreName;
            genres.appendChild(genre);
        });

        details.append(title, info, description, genres);
        card.append(poster, details);
        return card;
    }

    async function loadAdminMovies() {
        const result = await CES.api("/api/movies");
        if (!result.ok || !Array.isArray(result.data)) {
            throw new Error(result.data?.error || "Could not load saved movies.");
        }

        moviesList.replaceChildren();
        if (result.data.length === 0) {
            const empty = document.createElement("p");
            empty.className = "manage-movies-empty";
            empty.textContent = "No movies have been added yet.";
            moviesList.appendChild(empty);
            return;
        }
        result.data.forEach((movie) => moviesList.appendChild(createMovieCard(movie)));
    }

    if (
        moviesList && movieTitleInput && movieDescriptionInput && movieReleaseDateInput &&
        movieDurationInput && movieRatingInput && movieGenres && moviePosterInput &&
        moviePosterPrompt && moviePosterSelected && moviePosterFilename && moviePosterStatus
    ) {
        loadAdminMovies().catch((error) => {
            console.error("Could not load saved movies:", error);
            CES.toast(error.message, "error");
        });

        addMovieForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const posterFile = moviePosterInput.files[0];
            if (!posterFile) return;

            const submitButton = addMovieForm.querySelector('[type="submit"]');
            const formData = new FormData();
            formData.append("title", movieTitleInput.value.trim());
            formData.append("description", movieDescriptionInput.value.trim());
            formData.append("releaseDate", movieReleaseDateInput.value);
            formData.append("duration", movieDurationInput.value);
            formData.append("rating", movieRatingInput.value);
            movieGenres.querySelectorAll("[data-genre]").forEach((genreTag) => {
                formData.append("genres", genreTag.dataset.genre);
            });
            formData.append("poster", posterFile);
            submitButton.disabled = true;

            try {
                const result = await CES.api("/api/admin/movies", { method: "POST", body: formData });
                if (!result.ok || !result.data?.movie) {
                    const fieldErrors = Object.values(result.data?.errors || {}).join(" ");
                    CES.toast(fieldErrors || result.data?.error || "Could not save the movie.", "error");
                    return;
                }

                moviesList.querySelector(".manage-movies-empty")?.remove();
                moviesList.prepend(createMovieCard(result.data.movie));
                addMovieForm.reset();
                movieGenres.replaceChildren();
                moviePosterPrompt.classList.remove("hidden");
                moviePosterSelected.classList.add("hidden");
                moviePosterFilename.textContent = "";
                moviePosterStatus.textContent = "";
                moviePosterStatus.classList.remove("is-error");
                addMovieForm.classList.add("hidden");
                CES.toast(result.data.message || "Movie saved.", "success");
            } catch (error) {
                console.error("Could not save movie:", error);
                CES.toast(error.message || "Could not save the movie.", "error");
            } finally {
                submitButton.disabled = false;
            }
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
    let showtimeMoviesLoaded = false;
    let showroomsLoaded = false;

    function setShowtimeMessage(message, isError = false) {
        showtimeMessage.textContent = message;
        showtimeMessage.classList.toggle("is-error", isError);
    }

    function setShowtimeSuccess(showtime) {
        const movieTitle = document.createElement("strong");
        movieTitle.textContent = `Showtime added: ${showtime.movieTitle}`;

        const details = document.createElement("span");
        details.textContent = `${showtime.showroom} · ${showtime.date} · ${showtime.timeLabel}`;

        showtimeMessage.replaceChildren(movieTitle, details);
        showtimeMessage.classList.remove("is-error");
    }

    function updateShowtimeSubmit() {
        showtimeSubmit.disabled =
            !showtimeMoviesLoaded || !showroomsLoaded ||
            showtimeMovie.options.length < 2 || showtimeShowroom.options.length < 2;
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

    function createShowtimeCard(showtime) {
        const selectedDate = new Date(`${showtime.date}T00:00:00`);
        const dateLabel = selectedDate.toLocaleDateString(undefined, {
            year: "numeric",
            month: "long",
            day: "numeric"
        });
        const card = document.createElement("article");
        card.className = "scheduled-showtime-card";
        card.append(
            createShowtimeDetail("Movie", showtime.movieTitle),
            createShowtimeDetail("Date", dateLabel),
            createShowtimeDetail("Time", showtime.timeLabel),
            createShowtimeDetail("Showroom", showtime.showroom)
        );
        return card;
    }

    async function loadShowtimeMovies() {
        const result = await CES.api("/api/movies");
        if (!result.ok || !Array.isArray(result.data)) {
            throw new Error(result.data?.error || "Could not load movies for showtime scheduling.");
        }

        showtimeMovie.replaceChildren(new Option("Select a movie", ""));
        result.data.forEach((movie) => {
            if (!movie || typeof movie.title !== "string" || !movie.title.trim()) return;
            showtimeMovie.add(new Option(movie.title, String(movie.id)));
        });
        showtimeMoviesLoaded = true;
        updateShowtimeSubmit();
    }

    async function loadShowrooms() {
        const result = await CES.api("/api/admin/showrooms");
        if (!result.ok || !Array.isArray(result.data)) {
            throw new Error(result.data?.error || "Could not load showrooms.");
        }

        showtimeShowroom.replaceChildren(new Option("Select a showroom", ""));
        result.data.forEach((room) => {
            showtimeShowroom.add(new Option(room.name, String(room.id)));
        });
        showroomsLoaded = true;
        updateShowtimeSubmit();
    }

    async function loadScheduledShowtimes() {
        const result = await CES.api("/api/admin/showtimes");
        if (!result.ok || !Array.isArray(result.data)) {
            throw new Error(result.data?.error || "Could not load scheduled showtimes.");
        }

        scheduledShowtimesList.replaceChildren();
        if (result.data.length === 0) {
            const empty = document.createElement("p");
            empty.className = "scheduled-showtimes-empty";
            empty.id = "scheduled-showtimes-empty";
            empty.textContent = "No showtimes scheduled yet.";
            scheduledShowtimesList.appendChild(empty);
            return;
        }
        result.data.forEach((showtime) => {
            scheduledShowtimesList.appendChild(createShowtimeCard(showtime));
        });
    }

    const today = new Date();
    showtimeDate.min = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    showtimeForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!showtimeForm.reportValidity()) return;

        showtimeSubmit.disabled = true;
        try {
            const result = await CES.api("/api/admin/showtimes", {
                method: "POST",
                body: {
                    movieId: Number(showtimeMovie.value),
                    showroomId: Number(showtimeShowroom.value),
                    date: showtimeDate.value,
                    time: showtimeTime.value
                }
            });
            if (!result.ok || !result.data?.showtime) {
                const fieldErrors = Object.values(result.data?.errors || {}).join(" ");
                setShowtimeMessage(fieldErrors || result.data?.error || "Could not save the showtime.", true);
                return;
            }

            scheduledShowtimesList.querySelector(".scheduled-showtimes-empty")?.remove();
            scheduledShowtimesList.prepend(createShowtimeCard(result.data.showtime));
            showtimeForm.reset();
            setShowtimeSuccess(result.data.showtime);
        } catch (error) {
            console.error("Could not save showtime:", error);
            setShowtimeMessage(error.message || "Could not save the showtime.", true);
        } finally {
            updateShowtimeSubmit();
        }
    });

    loadShowtimeMovies().catch((error) => {
        console.error("Could not load movies for showtime scheduling:", error);
        setShowtimeMessage(error.message, true);
    });
    loadShowrooms().catch((error) => {
        console.error("Could not load showrooms:", error);
        setShowtimeMessage(error.message, true);
    });
    loadScheduledShowtimes().catch((error) => {
        console.error("Could not load scheduled showtimes:", error);
        setShowtimeMessage(error.message, true);
    });
}
