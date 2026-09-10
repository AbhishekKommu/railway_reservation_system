/* auth.js — wires up the login and register forms to the REST API. */

function showAlert(message) {
  const box = document.getElementById("alert-box");
  if (!box) return;
  box.textContent = message;
  box.classList.add("show");
}

function hideAlert() {
  const box = document.getElementById("alert-box");
  if (box) box.classList.remove("show");
}

const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();
    const btn = document.getElementById("login-btn");
    btn.disabled = true;
    btn.textContent = "Logging in...";

    try {
      await apiRequest("/api/login", {
        method: "POST",
        body: {
          email: document.getElementById("email").value.trim(),
          password: document.getElementById("password").value,
        },
      });
      window.location.href = "/dashboard";
    } catch (err) {
      showAlert(err.message);
      btn.disabled = false;
      btn.textContent = "Log In";
    }
  });
}

const registerForm = document.getElementById("register-form");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();
    const btn = document.getElementById("register-btn");
    btn.disabled = true;
    btn.textContent = "Creating account...";

    try {
      await apiRequest("/api/register", {
        method: "POST",
        body: {
          full_name: document.getElementById("full_name").value.trim(),
          email: document.getElementById("email").value.trim(),
          password: document.getElementById("password").value,
        },
      });
      window.location.href = "/dashboard";
    } catch (err) {
      showAlert(err.message);
      btn.disabled = false;
      btn.textContent = "Create Account";
    }
  });
}
