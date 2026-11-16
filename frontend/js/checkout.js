const CHECKOUT_KEY = "ces-checkout";
const PRICES = { adult: 12, child: 8, senior: 9 };

function getOrder() {
    try {
        return JSON.parse(sessionStorage.getItem(CHECKOUT_KEY));
    } catch {
        return null;
    }
}

function saveOrder(order) {
    sessionStorage.setItem(CHECKOUT_KEY, JSON.stringify(order));
}

function ticketCount(order) {
    return order.adult + order.child + order.senior;
}

function orderTotal(order) {
    return Object.keys(PRICES).reduce(function (sum, type) {
        return sum + order[type] * PRICES[type];
    }, 0);
}

function validOrder(order) {
    if (!order || typeof order.movie !== "string" ||
        !order.movie.trim() || !order.date || !order.time ||
        !Number.isSafeInteger(order.showId) || order.showId <= 0 ||
        typeof order.showroom !== "string" || !order.showroom.trim() ||
        !Array.isArray(order.seats)) {
        return false;
    }

    const quantitiesValid = Object.keys(PRICES).every(function (type) {
        return Number.isSafeInteger(order[type]) &&
            order[type] >= 0 && order[type] <= 40;
    });

    if (!quantitiesValid) return false;

    const count = ticketCount(order);

    return count > 0 && count <= 40 &&
        order.seats.length === count &&
        new Set(order.seats).size === count &&
        order.seats.every(function (seat) {
            return typeof seat === "string" &&
                /^[A-Z]+[1-9][0-9]*$/.test(seat);
        });
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function readText(id) {
    const element = document.getElementById(id);
    return element ? element.textContent.trim() : "";
}

function setupBooking() {
    const button = document.getElementById("proceed-to-checkout");
    if (!button) return;

    button.addEventListener("click", function () {
        const quantities = {};

        for (const type of Object.keys(PRICES)) {
            const input = document.getElementById(type + "-ticket");

            if (!input || !/^[0-9]+$/.test(input.value.trim())) {
                alert("Enter valid ticket quantities.");
                return;
            }

            const quantity = Number(input.value);

            if (!Number.isSafeInteger(quantity) || quantity > 40) {
                alert("Enter a quantity between 0 and 40.");
                return;
            }

            quantities[type] = quantity;
        }

        const count = Object.values(quantities).reduce(function (a, b) {
            return a + b;
        }, 0);

        if (count < 1 || count > 40) {
            alert("Select between 1 and 40 tickets.");
            return;
        }

        const selected = Array.from(
            document.querySelectorAll(".booking-seat.selected")
        );

        if (selected.some(function (seat) {
            return seat.disabled || seat.classList.contains("taken");
        })) {
            CES.toast("A selected seat is unavailable.", "error");
            return;
        }

        const seats = selected.map(function (seat) {
            return seat.textContent.trim();
        });

        if (seats.length !== count) {
            CES.toast(seats.length > count
                ? "You can select only " + count + " seats for your tickets."
                : "Select all " + count + " seats before continuing.", "error");
            return;
        }

        const params = new URLSearchParams(location.search);

        const order = {
            movie: readText("booking-movie-title"),
            date: readText("booking-date") || params.get("date"),
            time: readText("booking-showtime") || params.get("time"),
            showId: Number(params.get("showId")),
            showroom: readText("booking-showroom"),
            seats: seats,
            adult: quantities.adult,
            child: quantities.child,
            senior: quantities.senior,
            bookingUrl: location.pathname + location.search
        };

        if (!validOrder(order)) {
            CES.toast("Please select a valid movie and showtime.", "error");
            return;
        }

        saveOrder(order);
        location.href = "/pages/public/Checkout_Page.html";
    });
}

async function requireCustomer() {
    let user;

    try {
        user = await CES.currentUser(true);
    } catch {
        alert("Unable to verify your account.");
        return null;
    }

    if (!user) {
        const next = encodeURIComponent(
            location.pathname + location.search
        );

        location.replace("/pages/auth/Login_Page.html?next=" + next);
        return null;
    }

    return user;
}

function renderTickets(order) {
    const container = document.getElementById("order-tickets");
    container.replaceChildren();

    Object.keys(PRICES).forEach(function (type) {
        if (order[type] === 0) return;

        const row = document.createElement("div");
        row.className = "checkout-ticket-row";

        const label = document.createElement("span");
        label.textContent =
            type.charAt(0).toUpperCase() +
            type.slice(1) + " x " + order[type];

        const price = document.createElement("span");
        price.textContent = "$" +
            (order[type] * PRICES[type]).toFixed(2);

        row.append(label, price);
        container.appendChild(row);
    });
}

async function setupCheckout() {
    const form = document.getElementById("checkout-form");
    if (!form) return;

    const order = getOrder();

    if (!validOrder(order)) {
        alert("Please select your tickets and seats first.");
        location.replace("/pages/public/Home_Page.html");
        return;
    }

    const user = await requireCustomer();
    if (!user) return;

    setText("order-movie", order.movie);
    setText("order-date", order.date);
    setText("order-time", order.time);
    setText("order-showroom", order.showroom);
    setText("order-seats", order.seats.join(", "));
    setText("order-count", ticketCount(order));
    setText("order-total", orderTotal(order).toFixed(2));

    renderTickets(order);

    const email = document.getElementById("checkout-email");
    email.value = order.email || user.email || "";

    document.getElementById("back-to-booking").addEventListener(
        "click",
        function () {
            location.href = order.bookingUrl &&
                order.bookingUrl.startsWith("/pages/public/Booking_Page.html")
                ? order.bookingUrl
                : "/pages/public/Home_Page.html";
        }
    );

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        const value = email.value.trim();
        const error = document.getElementById("checkout-error");
        error.hidden = true;

        if (value.length > 254 ||
            !/^[^ @]+@[^ @]+[.][^ @]+$/.test(value)) {
            error.textContent = "Enter a valid email address.";
            error.hidden = false;
            return;
        }

        order.email = value;
        saveOrder(order);
        location.href = "/pages/public/Payment_Page.html";
    });
}

async function setupPayment() {
    if (!document.getElementById("payment-movie")) return;

    const order = getOrder();

    if (!validOrder(order) || typeof order.email !== "string" ||
        !/^[^ @]+@[^ @]+[.][^ @]+$/.test(order.email)) {
        location.replace("/pages/public/Checkout_Page.html");
        return;
    }

    const user = await requireCustomer();
    if (!user) return;

    setText("payment-movie", order.movie);
    setText("payment-date", order.date);
    setText("payment-time", order.time);
    setText("payment-showroom", order.showroom);
    setText("payment-seats", order.seats.join(", "));
    setText("payment-email", order.email);
    setText("payment-total", orderTotal(order).toFixed(2));

    document.getElementById("back-to-checkout").addEventListener(
        "click",
        function () {
            location.href = "/pages/public/Checkout_Page.html";
        }
    );
}

document.addEventListener("DOMContentLoaded", function () {
    setupBooking();
    setupCheckout();
    setupPayment();
});
