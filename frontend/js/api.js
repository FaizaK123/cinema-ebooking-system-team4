/* Shared helpers for talking to the backend (loaded before script.js and account.js). */
window.CES = (function () {
    /* Calls the API and always resolves to { ok, status, data } instead of throwing. */
    async function api(path, options = {}) {
        const init = {
            method: options.method || "GET",
            headers: { "Accept": "application/json" },
            credentials: "same-origin"
        };
        if (options.body !== undefined) {
            init.headers["Content-Type"] = "application/json";
            init.body = JSON.stringify(options.body);
        }
        let response;
        try {
            response = await fetch(path, init);
        } catch (error) {
            return { ok: false, status: 0, data: { error: "We couldn't reach the server. Check your connection and try again." } };
        }
        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }
        if (!response.ok && !data.error) {
            data.error = "Something went wrong. Please try again.";
        }
        return { ok: response.ok, status: response.status, data };
    }

    /* The logged-in user ({ firstName, role, ... }) or null. Cached for the page. */
    let currentUserPromise = null;
    function currentUser(refresh = false) {
        if (!currentUserPromise || refresh) {
            currentUserPromise = api("/api/auth/me").then(function (result) {
                return result.ok && result.data.loggedIn ? result.data.user : null;
            });
        }
        return currentUserPromise;
    }

    /* Shows text in a message element; type is "error", "success" or "info". */
    function showMessage(element, text, type = "error") {
        if (!element) return;
        element.textContent = text || "";
        element.classList.remove("error", "success", "info");
        element.classList.add(type);
        element.hidden = !text;
    }

    /* Puts each API field error under its input (elements with data-error-for="fieldName"). */
    function showFieldErrors(form, errors = {}) {
        form.querySelectorAll("[data-error-for]").forEach(function (element) {
            const message = errors[element.dataset.errorFor];
            element.textContent = message || "";
            element.hidden = !message;
            const input = form.querySelector(`[data-field="${element.dataset.errorFor}"]`);
            if (input) {
                input.classList.toggle("input-invalid", Boolean(message));
                input.setAttribute("aria-invalid", message ? "true" : "false");
            }
        });
        const firstInvalid = form.querySelector(".input-invalid");
        if (firstInvalid) firstInvalid.focus();
    }

    document.addEventListener("input", function (event) {
        const field = event.target.dataset && event.target.dataset.field;
        if (!field) return;
        event.target.classList.remove("input-invalid");
        event.target.removeAttribute("aria-invalid");
        const form = event.target.closest("form");
        const error = form && form.querySelector(`[data-error-for="${CSS.escape(field)}"]`);
        if (error) error.hidden = true;
    });

    /* Short pop-up message in the corner of the screen. */
    function toast(text, type = "success") {
        let box = document.getElementById("ces-toast");
        if (!box) {
            box = document.createElement("div");
            box.id = "ces-toast";
            box.className = "toast";
            box.setAttribute("role", "status");
            document.body.appendChild(box);
        }
        box.textContent = text;
        box.dataset.type = type;
        box.classList.add("visible");
        clearTimeout(box.hideTimer);
        box.hideTimer = setTimeout(function () { box.classList.remove("visible"); }, 3500);
    }

    function loginUrl() {
        return "Login_Page.html?next=" + encodeURIComponent(window.location.pathname + window.location.search);
    }

    /* ---- Favorites (customers only) ---- */
    let favoriteIdsPromise = null;
    function favoriteIds() {
        if (!favoriteIdsPromise) {
            favoriteIdsPromise = currentUser().then(async function (user) {
                if (!user || user.role !== "CUSTOMER") return new Set();
                const result = await api("/api/profile/favorites");
                return new Set(result.ok ? result.data.map(function (movie) { return movie.id; }) : []);
            });
        }
        return favoriteIdsPromise;
    }

    /* Adds or removes a favorite. Returns true/false for the new state, or null if nothing changed. */
    async function toggleFavorite(movieId) {
        const user = await currentUser();
        if (!user) {
            toast("Log in to save movies to your favorites.", "info");
            setTimeout(function () { window.location.href = loginUrl(); }, 1200);
            return null;
        }
        if (user.role !== "CUSTOMER") {
            toast("Favorites are only available for customer accounts.", "error");
            return null;
        }
        const ids = await favoriteIds();
        const isFavorite = ids.has(movieId);
        const result = isFavorite
            ? await api(`/api/profile/favorites/${movieId}`, { method: "DELETE" })
            : await api("/api/profile/favorites", { method: "POST", body: { movieId } });
        if (!result.ok) {
            toast(result.data.error, "error");
            return null;
        }
        if (isFavorite) ids.delete(movieId); else ids.add(movieId);
        toast(result.data.message, "success");
        return !isFavorite;
    }

    /* Updates a heart button's icon, tooltip and screen-reader label. */
    function setHeartState(button, isFavorite) {
        const label = isFavorite ? "Remove from favorites" : "Add to favorites";
        button.title = label;
        button.setAttribute("aria-label", label);
        button.setAttribute("aria-pressed", String(isFavorite));
        button.classList.toggle("is-favorite", isFavorite);
        const icon = button.querySelector("i");
        if (icon) {
            icon.classList.toggle("fa-solid", isFavorite);
            icon.classList.toggle("fa-regular", !isFavorite);
        }
    }

    async function logout() {
        await api("/api/auth/logout", { method: "POST" });
        window.location.href = "Home_Page.html?loggedOut=1";
    }

    return { api, currentUser, showMessage, showFieldErrors, toast, loginUrl, favoriteIds, toggleFavorite, setHeartState, logout };
})();
