/* Account pages: login, signup, forgot/reset password, profile, address, payment cards, admin portal.
   Each section only runs on the page that has its form/element. Requires js/api.js. */

function formatPhone(digits) {
    const d = String(digits || "").replace(/\D/g, "");
    return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : d;
}

function setBusy(button, busy, busyText) {
    if (!button) return;
    if (busy) {
        button.dataset.label = button.textContent;
        button.textContent = busyText;
    } else if (button.dataset.label) {
        button.textContent = button.dataset.label;
    }
    button.disabled = busy;
}

/* Groups card digits as 4111 1111 1111 1111 while typing */
function formatCardInput(input) {
    input.addEventListener("input", () => {
        const digits = input.value.replace(/\D/g, "").slice(0, 19);
        input.value = digits.replace(/(\d{4})(?=\d)/g, "$1 ");
    });
}

/* ---------------------------------------------------------------- Show / hide password buttons */
document.querySelectorAll("[data-toggle-password]").forEach((toggle) => {
    const input = document.getElementById(toggle.getAttribute("aria-controls"));
    if (!input) return;
    toggle.addEventListener("click", () => {
        const isVisible = input.type === "text";
        input.type = isVisible ? "password" : "text";
        toggle.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
        toggle.setAttribute("aria-pressed", String(!isVisible));
        toggle.title = isVisible ? "Show password" : "Hide password";
        const icon = toggle.querySelector("i");
        icon.classList.toggle("fa-eye", isVisible);
        icon.classList.toggle("fa-eye-slash", !isVisible);
    });
});

/* ---------------------------------------------------------------- Login page */
const loginForm = document.getElementById("login-form");
if (loginForm) {
    const params = new URLSearchParams(window.location.search);
    const message = document.getElementById("login-message");
    const resendButton = document.getElementById("resend-verification-btn");
    const submitButton = loginForm.querySelector("button[type='submit']");
    let unverifiedEmail = null;

    if (params.get("verified") === "1") {
        CES.showMessage(message, "Your email is confirmed and your account is active. You can log in now!", "success");
    } else if (params.get("verified") === "invalid") {
        CES.showMessage(message, "That confirmation link is invalid or has expired. Log in to get a new one.", "error");
    } else if (params.get("reset") === "1") {
        CES.showMessage(message, "Your password has been reset. Log in with your new password.", "success");
    } else if (params.get("next")) {
        CES.showMessage(message, "Please log in to continue.", "info");
    }

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(loginForm, {});
        CES.showMessage(message, "");
        resendButton.hidden = true;

        setBusy(submitButton, true, "Logging in...");
        const result = await CES.api("/api/auth/login", {
            method: "POST",
            body: {
                identifier: document.getElementById("login-identifier").value.trim(),
                password: document.getElementById("login-password").value,
                remember: document.getElementById("login-remember").checked,
                next: params.get("next") || ""
            }
        });
        setBusy(submitButton, false);

        if (result.ok) {
            CES.showMessage(message, result.data.message, "success");
            window.location.href = result.data.redirect;
            return;
        }
        if (result.data.errors) {
            CES.showFieldErrors(loginForm, result.data.errors);
        } else {
            CES.showMessage(message, result.data.error, "error");
        }
        if (result.data.code === "UNVERIFIED") {
            unverifiedEmail = result.data.email;
            resendButton.hidden = false;
        }
    });

    resendButton.addEventListener("click", async () => {
        setBusy(resendButton, true, "Sending...");
        const result = await CES.api("/api/auth/resend-verification", {
            method: "POST", body: { email: unverifiedEmail }
        });
        setBusy(resendButton, false);
        CES.showMessage(message, result.data.message || result.data.error, result.ok ? "success" : "error");
        if (result.ok) resendButton.hidden = true;
    });
}

/* ---------------------------------------------------------------- Signup page */
const signupForm = document.getElementById("signup-form");
if (signupForm) {
    const message = document.getElementById("signup-form-message");
    const submitButton = signupForm.querySelector("button[type='submit']");
    const addressToggle = document.getElementById("signup-add-address");
    const addressFields = document.getElementById("signup-address-fields");
    const cardList = document.getElementById("signup-card-list");
    const addCardButton = document.getElementById("signup-add-card");
    const cardTemplate = document.getElementById("signup-card-template");
    const MAX_CARDS = 3;

    addressToggle.addEventListener("change", () => {
        addressFields.hidden = !addressToggle.checked;
        addressFields.querySelectorAll("input").forEach((input) => { input.required = addressToggle.checked; });
    });

    /* Card blocks get numbered field names (cards.0.number, ...) so server errors land on the right input */
    function renumberCards() {
        const blocks = cardList.querySelectorAll(".signup-card");
        blocks.forEach((block, index) => {
            block.querySelector(".signup-card-title").textContent = `Card ${index + 1}`;
            block.querySelectorAll("[data-card-field]").forEach((element) => {
                const key = `cards.${index}.${element.dataset.cardField}`;
                if (element.matches("input")) {
                    element.dataset.field = key;
                    element.id = `card-${index}-${element.dataset.cardField}`;
                } else {
                    element.dataset.errorFor = key;
                }
            });
            block.querySelectorAll("label[data-for-field]").forEach((label) => {
                label.htmlFor = `card-${index}-${label.dataset.forField}`;
            });
        });
        addCardButton.disabled = blocks.length >= MAX_CARDS;
        addCardButton.textContent = blocks.length >= MAX_CARDS
            ? "Maximum of 3 cards added"
            : blocks.length ? "Add Another Payment Card" : "Add Payment Card";
    }

    addCardButton.addEventListener("click", () => {
        if (cardList.children.length >= MAX_CARDS) return;
        const block = cardTemplate.content.firstElementChild.cloneNode(true);
        block.querySelector(".signup-card-remove").addEventListener("click", () => {
            block.remove();
            renumberCards();
        });
        formatCardInput(block.querySelector("[data-card-field='number']"));
        cardList.appendChild(block);
        renumberCards();
        block.querySelector("input").focus();
    });

    signupForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(signupForm, {});
        CES.showMessage(message, "");

        const value = (id) => document.getElementById(id).value;
        const body = {
            firstName: value("signup-first-name").trim(),
            lastName: value("signup-last-name").trim(),
            email: value("signup-email").trim(),
            phone: value("signup-phone").trim(),
            password: value("signup-password"),
            confirmPassword: value("signup-confirm-password"),
            promoOptIn: document.getElementById("signup-promo").checked,
            address: addressToggle.checked ? {
                street: value("signup-street").trim(),
                city: value("signup-city").trim(),
                state: value("signup-state").trim(),
                zip: value("signup-zip").trim()
            } : null,
            cards: Array.from(cardList.querySelectorAll(".signup-card")).map((block) => {
                const field = (name) => block.querySelector(`[data-card-field='${name}']`).value.trim();
                return {
                    cardholderName: field("cardholderName"),
                    number: field("number"),
                    expiration: field("expiration"),
                    cvv: field("cvv")
                };
            })
        };

        setBusy(submitButton, true, "Creating account...");
        const result = await CES.api("/api/auth/register", { method: "POST", body });
        setBusy(submitButton, false);

        if (result.ok) {
            signupForm.hidden = true;
            const success = document.getElementById("signup-success");
            document.getElementById("signup-success-text").textContent = result.data.message;
            success.hidden = false;
            success.querySelector("a").focus();
            return;
        }
        CES.showFieldErrors(signupForm, result.data.errors || {});
        CES.showMessage(message, result.data.error, "error");
    });
}

/* ---------------------------------------------------------------- Forgot password (request link) */
const forgotPasswordForm = document.getElementById("forgot-password-form");
if (forgotPasswordForm) {
    const message = document.getElementById("forgot-password-message");
    const submitButton = forgotPasswordForm.querySelector("button[type='submit']");

    forgotPasswordForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(forgotPasswordForm, {});
        setBusy(submitButton, true, "Sending...");
        const result = await CES.api("/api/auth/forgot-password", {
            method: "POST", body: { email: document.getElementById("fp-email").value.trim() }
        });
        setBusy(submitButton, false);
        if (result.data.errors) {
            CES.showFieldErrors(forgotPasswordForm, result.data.errors);
            CES.showMessage(message, "");
            return;
        }
        CES.showMessage(message, result.data.message || result.data.error, result.ok ? "success" : "error");
    });
}

/* ---------------------------------------------------------------- Reset password (from emailed link) */
const resetPasswordForm = document.getElementById("reset-password-form");
if (resetPasswordForm) {
    const token = new URLSearchParams(window.location.search).get("token");
    const message = document.getElementById("reset-password-message");
    const submitButton = resetPasswordForm.querySelector("button[type='submit']");
    const invalidLinkText = "This reset link is invalid or has expired. Please request a new one.";

    function disableForm() {
        resetPasswordForm.querySelectorAll("input, button[type='submit']").forEach((el) => { el.disabled = true; });
        document.getElementById("reset-new-link").hidden = false;
    }

    if (!token) {
        CES.showMessage(message, "Open the reset link from your email to choose a new password.", "error");
        disableForm();
    } else {
        CES.api(`/api/auth/reset-password/check?token=${encodeURIComponent(token)}`).then((result) => {
            if (!result.ok || !result.data.valid) {
                CES.showMessage(message, invalidLinkText, "error");
                disableForm();
            }
        });
    }

    resetPasswordForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(resetPasswordForm, {});
        CES.showMessage(message, "");
        setBusy(submitButton, true, "Saving...");
        const result = await CES.api("/api/auth/reset-password", {
            method: "POST",
            body: {
                token,
                password: document.getElementById("new-password").value,
                confirmPassword: document.getElementById("confirm-password").value
            }
        });
        setBusy(submitButton, false);
        if (result.ok) {
            window.location.href = "Login_Page.html?reset=1";
            return;
        }
        if (result.data.errors) CES.showFieldErrors(resetPasswordForm, result.data.errors);
        CES.showMessage(message, result.data.error, "error");
        if (result.data.code === "INVALID_TOKEN") disableForm();
    });
}

/* ---------------------------------------------------------------- Profile page */
const profilePage = document.getElementById("profile-page");
if (profilePage) {
    const infoForm = document.getElementById("profile-info-form");
    const infoMessage = document.getElementById("profile-info-message");
    const passwordForm = document.getElementById("profile-password-form");
    const passwordMessage = document.getElementById("profile-password-message");
    const addressText = document.getElementById("profile-address-text");
    const addressEdit = document.getElementById("profile-address-edit");
    const addressRemove = document.getElementById("profile-address-remove");
    const cardList = document.getElementById("profile-card-list");
    const addCardLink = document.getElementById("profile-add-card");
    const cardNote = document.getElementById("profile-card-note");

    const saved = new URLSearchParams(window.location.search).get("saved");
    if (saved === "address") CES.toast("Your address has been saved.");
    if (saved === "card") CES.toast("Your payment card has been saved.");

    async function loadProfile() {
        const result = await CES.api("/api/profile");
        if (!result.ok) {
            if (result.status === 401) window.location.href = CES.loginUrl();
            CES.showMessage(infoMessage, result.data.error, "error");
            return;
        }
        const profile = result.data;
        document.getElementById("profile-greeting").textContent = `Hi, ${profile.firstName}!`;
        document.getElementById("profile-first-name").value = profile.firstName;
        document.getElementById("profile-last-name").value = profile.lastName;
        document.getElementById("profile-email").value = profile.email;
        document.getElementById("profile-phone").value = formatPhone(profile.phone);
        document.getElementById("profile-promo").checked = profile.promoOptIn;

        if (profile.address) {
            const a = profile.address;
            addressText.textContent = `${a.street}, ${a.city}, ${a.state} ${a.zip}`;
            addressEdit.textContent = "Edit Address";
            addressRemove.hidden = false;
        } else {
            addressText.textContent = "No address saved yet.";
            addressEdit.textContent = "Add Address";
            addressRemove.hidden = true;
        }

        cardList.replaceChildren();
        if (profile.cards.length === 0) {
            const empty = document.createElement("li");
            empty.className = "profile-empty";
            empty.textContent = "No payment cards saved yet.";
            cardList.appendChild(empty);
        }
        profile.cards.forEach((card) => {
            const item = document.createElement("li");
            item.className = "profile-card-item";
            const text = document.createElement("span");
            const month = String(card.expMonth).padStart(2, "0");
            text.textContent = `${card.brand} ending in ${card.lastFour} · ${card.cardholderName || ""} · expires ${month}/${card.expYear}`;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "btn-secondary btn-small";
            remove.textContent = "Remove";
            remove.setAttribute("aria-label", `Remove card ending in ${card.lastFour}`);
            remove.addEventListener("click", () => removeCard(card));
            item.append(text, remove);
            cardList.appendChild(item);
        });
        const full = profile.cards.length >= profile.maxCards;
        addCardLink.classList.toggle("disabled", full);
        addCardLink.setAttribute("aria-disabled", String(full));
        cardNote.textContent = full
            ? `You've saved the maximum of ${profile.maxCards} cards. Remove one to add another.`
            : `You can save up to ${profile.maxCards} cards (${profile.cards.length} saved).`;
    }

    async function removeCard(card) {
        if (!confirm(`Remove the ${card.brand} card ending in ${card.lastFour}?`)) return;
        const result = await CES.api(`/api/profile/cards/${card.id}`, { method: "DELETE" });
        CES.toast(result.data.message || result.data.error, result.ok ? "success" : "error");
        loadProfile();
    }

    addCardLink.addEventListener("click", (event) => {
        if (addCardLink.classList.contains("disabled")) {
            event.preventDefault();
            CES.toast(cardNote.textContent, "error");
        }
    });

    addressRemove.addEventListener("click", async () => {
        if (!confirm("Remove your saved address?")) return;
        const result = await CES.api("/api/profile/address", { method: "DELETE" });
        CES.toast(result.data.message || result.data.error, result.ok ? "success" : "error");
        loadProfile();
    });

    infoForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(infoForm, {});
        const button = infoForm.querySelector("button[type='submit']");
        setBusy(button, true, "Saving...");
        const result = await CES.api("/api/profile", {
            method: "PUT",
            body: {
                firstName: document.getElementById("profile-first-name").value.trim(),
                lastName: document.getElementById("profile-last-name").value.trim(),
                phone: document.getElementById("profile-phone").value.trim(),
                promoOptIn: document.getElementById("profile-promo").checked
            }
        });
        setBusy(button, false);
        if (result.data.errors) CES.showFieldErrors(infoForm, result.data.errors);
        CES.showMessage(infoMessage, result.data.message || result.data.error, result.ok ? "success" : "error");
        if (result.ok) {
            CES.currentUser(true);
            loadProfile();
        }
    });

    passwordForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(passwordForm, {});
        const button = passwordForm.querySelector("button[type='submit']");
        setBusy(button, true, "Saving...");
        const result = await CES.api("/api/profile/password", {
            method: "PUT",
            body: {
                currentPassword: document.getElementById("profile-current-password").value,
                newPassword: document.getElementById("profile-new-password").value,
                confirmPassword: document.getElementById("profile-confirm-password").value
            }
        });
        setBusy(button, false);
        if (result.data.errors) CES.showFieldErrors(passwordForm, result.data.errors);
        CES.showMessage(passwordMessage, result.data.message || result.data.error, result.ok ? "success" : "error");
        if (result.ok) passwordForm.reset();
    });

    /* Favorite movies: view and remove (adding happens while browsing, with the heart icon) */
    async function loadFavorites() {
        const grid = document.getElementById("profile-favorites");
        const result = await CES.api("/api/profile/favorites");
        grid.replaceChildren();
        if (!result.ok || result.data.length === 0) {
            const empty = document.createElement("p");
            empty.className = "profile-empty";
            empty.textContent = result.ok
                ? "No favorites yet. Tap the heart on any movie while browsing to add it here."
                : result.data.error;
            grid.appendChild(empty);
            return;
        }
        result.data.forEach((movie) => {
            const card = document.createElement("div");
            card.className = "profile-favorite";
            const link = document.createElement("a");
            link.href = `Movie_Page.html?id=${movie.id}`;
            const poster = document.createElement("img");
            poster.src = movie.poster;
            poster.alt = movie.title;
            const title = document.createElement("span");
            title.textContent = movie.title;
            link.append(poster, title);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "btn-secondary btn-small";
            remove.innerHTML = '<i class="fa-solid fa-heart-crack"></i> Remove';
            remove.title = "Remove from favorites";
            remove.addEventListener("click", async () => {
                const removed = await CES.api(`/api/profile/favorites/${movie.id}`, { method: "DELETE" });
                CES.toast(removed.data.message || removed.data.error, removed.ok ? "success" : "error");
                loadFavorites();
            });
            card.append(link, remove);
            grid.appendChild(card);
        });
    }

    /* Movie preferences: favorite genres */
    async function loadGenres() {
        const list = document.getElementById("profile-genre-list");
        const result = await CES.api("/api/profile/genres");
        list.replaceChildren();
        if (!result.ok) return;
        result.data.available.forEach((genre) => {
            const id = `genre-pref-${genre.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
            const label = document.createElement("label");
            label.className = "form-check";
            label.htmlFor = id;
            const box = document.createElement("input");
            box.type = "checkbox";
            box.id = id;
            box.value = genre;
            box.checked = result.data.genres.includes(genre);
            label.append(box, document.createTextNode(` ${genre}`));
            list.appendChild(label);
        });
    }

    document.getElementById("profile-genre-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const genres = Array.from(document.querySelectorAll("#profile-genre-list input:checked")).map((box) => box.value);
        const result = await CES.api("/api/profile/genres", { method: "PUT", body: { genres } });
        CES.showMessage(document.getElementById("profile-genre-message"),
            result.data.message || result.data.error, result.ok ? "success" : "error");
    });

    loadProfile();
    loadFavorites();
    loadGenres();
}

/* ---------------------------------------------------------------- Address page (profile) */
const addressForm = document.getElementById("address-form");
if (addressForm) {
    const message = document.getElementById("address-form-message");
    const submitButton = addressForm.querySelector("button[type='submit']");

    CES.api("/api/profile").then((result) => {
        if (result.ok && result.data.address) {
            ["street", "city", "state", "zip"].forEach((field) => {
                document.getElementById(field).value = result.data.address[field];
            });
            document.getElementById("address-page-title").textContent = "Edit Address";
            submitButton.textContent = "Save Address";
        }
    });

    addressForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(addressForm, {});
        setBusy(submitButton, true, "Saving...");
        const result = await CES.api("/api/profile/address", {
            method: "PUT",
            body: {
                street: document.getElementById("street").value.trim(),
                city: document.getElementById("city").value.trim(),
                state: document.getElementById("state").value.trim(),
                zip: document.getElementById("zip").value.trim()
            }
        });
        setBusy(submitButton, false);
        if (result.ok) {
            window.location.href = "Profile_Page.html?saved=address";
            return;
        }
        if (result.data.errors) CES.showFieldErrors(addressForm, result.data.errors);
        CES.showMessage(message, result.data.error, "error");
    });
}

/* ---------------------------------------------------------------- Payment card page (profile) */
const paymentForm = document.getElementById("payment-form");
if (paymentForm) {
    const message = document.getElementById("payment-form-message");
    const submitButton = paymentForm.querySelector("button[type='submit']");
    formatCardInput(document.getElementById("card-num"));

    CES.api("/api/profile/cards").then((result) => {
        if (result.ok && result.data.cards.length >= result.data.maxCards) {
            CES.showMessage(message,
                `You've saved the maximum of ${result.data.maxCards} cards. Remove one from your profile to add another.`, "error");
            submitButton.disabled = true;
        }
    });

    paymentForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        CES.showFieldErrors(paymentForm, {});
        CES.showMessage(message, "");
        setBusy(submitButton, true, "Saving...");
        const result = await CES.api("/api/profile/cards", {
            method: "POST",
            body: {
                cardholderName: document.getElementById("card-name").value.trim(),
                number: document.getElementById("card-num").value.trim(),
                expiration: document.getElementById("expire").value,
                cvv: document.getElementById("cvv").value.trim()
            }
        });
        setBusy(submitButton, false);
        if (result.ok) {
            window.location.href = "Profile_Page.html?saved=card";
            return;
        }
        if (result.data.errors) CES.showFieldErrors(paymentForm, result.data.errors);
        CES.showMessage(message, result.data.error, "error");
    });
}

/* ---------------------------------------------------------------- Admin portal (prototype) */
const adminPortal = document.getElementById("admin-portal");
if (adminPortal) {
    CES.api("/api/admin/summary").then((result) => {
        if (!result.ok) {
            if (result.status === 401) window.location.href = CES.loginUrl();
            return;
        }
        const s = result.data;
        document.getElementById("admin-greeting").textContent = `Welcome, ${s.adminName}`;
        document.getElementById("admin-stat-movies").textContent = `${s.movies} movies (${s.currentlyRunning} now playing)`;
        document.getElementById("admin-stat-customers").textContent = `${s.customers} customers (${s.activeCustomers} active)`;
        document.getElementById("admin-stat-promotions").textContent = `${s.promotions} promotions`;
    });

    document.querySelectorAll(".admin-menu-item").forEach((item) => {
        item.addEventListener("click", () => {
            CES.toast(`${item.dataset.section} will be built in a later sprint.`, "info");
        });
    });

    document.getElementById("admin-logout").addEventListener("click", () => CES.logout());
}
