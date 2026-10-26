const popup = document.getElementById("login-popup");
const loginButton = document.getElementById("nav-bar-login-btn");
let isPopupVisible = false;

async function loadLoginPopup() {
    if (isPopupVisible) return;
    const res = await fetch('/components/Login_Popup.html');
    if (!res.ok) throw new Error('Failed to load login popup');
    popup.innerHTML = await res.text();
    await wireLoginPopup();
    isPopupVisible = true;
}

function openLoginPopup() {
    popup.hidden = false;
    loginButton.setAttribute('aria-expanded', 'true');
}

function closeLoginPopup() {
    popup.hidden = true;
    loginButton.setAttribute('aria-expanded', 'false');
}

async function wireLoginPopup() {
    popup.querySelector('#login-popup-close-btn').addEventListener('click', closeLoginPopup);
    const user = window.CES ? await CES.currentUser() : null;

    if (user) {
        // Logged in: greet the user and offer their account page and Logout instead of Login / Sign Up
        const isAdmin = user.role === 'ADMIN';
        popup.querySelector('.login-popup-greeting').textContent = `Hi, ${user.firstName}!`;
        popup.querySelector('.login-popup-buttons').innerHTML = `
            <button class="login-popup-button login" id="login-popup-account-btn">${isAdmin ? 'Admin Portal' : 'My Profile'}</button>
            <button class="login-popup-button sign-up" id="login-popup-logout-btn"><i class="fa-solid fa-right-from-bracket"></i> Logout</button>`;
        popup.querySelector('#login-popup-account-btn').addEventListener('click', () => {
            window.location.href = isAdmin ? 'Admin_Home.html' : 'Profile_Page.html';
        });
        popup.querySelector('#login-popup-logout-btn').addEventListener('click', () => CES.logout());
        return;
    }

    popup.querySelector('#login-popup-login-btn').addEventListener('click',  () => {
        window.location.href = window.CES ? CES.loginUrl() : 'Login_Page.html';
    });
    popup.querySelector('#login-popup-signup-btn').addEventListener('click',  () => {
        window.location.href = 'Signup_Page.html';
    });
}

if (popup && loginButton) {
    loginButton.addEventListener('click', async () => {
        if (!popup.hidden) return closeLoginPopup();
        try {
            await loadLoginPopup();
            openLoginPopup();
        } catch (error) {
            console.error('Error loading login popup:', error);
        }
    });

    // Show at a glance whether someone is logged in
    if (window.CES) {
        CES.currentUser().then((user) => {
            if (!user) return;
            loginButton.classList.add('logged-in');
            loginButton.title = `Logged in as ${user.firstName}`;
            loginButton.setAttribute('aria-label', `Account menu for ${user.firstName}`);
        });
    }
}
