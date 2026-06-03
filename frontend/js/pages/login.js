import { apiGet, apiPost } from '../api.js';
import { isAuthenticated, setToken, setUsername } from '../auth.js';
import { initTheme, toggleTheme } from '../theme.js';

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();

  if (isAuthenticated()) {
    window.location.href = '/rooms';
    return;
  }

  document.querySelector('.theme-toggle').addEventListener('click', toggleTheme);

  const errorEl = document.getElementById('login-error');

  let mode = 'LOCAL';
  try {
    const result = await apiGet('/auth/mode');
    mode = result.mode;
  } catch {
    mode = 'LOCAL';
  }

  if (mode === 'LOCAL') {
    const form = document.getElementById('local-login-form');
    form.hidden = false;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      const username = document.getElementById('username').value.trim();
      if (!username) return;
      try {
        const result = await apiPost('/auth/local-login', { username });
        setToken(result.access_token);
        setUsername(username);
        window.location.href = '/rooms';
      } catch (err) {
        errorEl.textContent = err.detail || 'Login failed';
        errorEl.hidden = false;
      }
    });
  } else {
    const container = document.getElementById('online-auth');
    container.hidden = false;

    const tabs = container.querySelectorAll('.tab');
    const loginForm = document.getElementById('online-login-form');
    const registerForm = document.getElementById('online-register-form');

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        errorEl.hidden = true;
        if (tab.dataset.tab === 'login') {
          loginForm.hidden = false;
          registerForm.hidden = true;
        } else {
          loginForm.hidden = true;
          registerForm.hidden = false;
        }
      });
    });

    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      const identifier = loginForm.identifier.value.trim();
      const password = loginForm.password.value;
      try {
        const result = await apiPost('/auth/login', { identifier, password });
        setToken(result.access_token);
        setUsername(identifier);
        window.location.href = '/rooms';
      } catch (err) {
        errorEl.textContent = err.detail || 'Invalid credentials';
        errorEl.hidden = false;
      }
    });

    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      const username = registerForm.username.value.trim();
      const email = registerForm.email.value.trim();
      const password = registerForm.password.value;
      try {
        await apiPost('/auth/register', { username, email, password });
        tabs[0].click();
        errorEl.textContent = '';
        loginForm.identifier.value = username;
      } catch (err) {
        errorEl.textContent = err.detail || 'Registration failed';
        errorEl.hidden = false;
      }
    });
  }
});
