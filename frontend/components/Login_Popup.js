const popup = document.getElementById("login-popup");
const loginButton = document.getElementById("nav-bar-login-btn");
let isPopupVisible = false;

async function loadLoginPopup() {
    if (isPopupVisible) return;
    const res = await fetch('/components/Login_Popup.html');
    if (!res.ok) throw new Error('Failed to load login popup');
    popup.innerHTML = await res.text();
    wireLoginPopup();
    isPopupVisible = true;
}

function openLoginPopup() {
    console.log('Opening login popup');
    popup.hidden = false;
    loginButton.setAttribute('aria-expanded', 'true');
}

function closeLoginPopup() {
    popup.hidden = true;
    loginButton.setAttribute('aria-expanded', 'false');
}

function wireLoginPopup() {
    popup.querySelector('#login-popup-close-btn').addEventListener('click', closeLoginPopup);
    popup.querySelector('#login-popup-login-btn').addEventListener('click',  () => {
        window.location.href = 'Login_Page.html';
    });
    popup.querySelector('#login-popup-signup-btn').addEventListener('click',  () => {
        window.location.href = 'Signup_Page.html';
    });
}

loginButton.addEventListener('click', async () => {
    if (!popup.hidden) return closeLoginPopup();
    try {
        await loadLoginPopup();
        openLoginPopup();
    } catch (error) {
        console.error('Error loading login popup:', error);
    }
});

