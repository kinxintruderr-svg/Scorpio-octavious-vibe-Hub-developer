
/*
 * SOV Develop Hub — frontend connection
 *
 * Before testing:
 * 1. Set API_BASE_URL to your deployed Develop Hub API URL.
 * 2. Set GOOGLE_CLIENT_ID to your Google Web OAuth client ID.
 * 3. Load this file from index.html.
 */

const API_BASE_URL = ""; // Example: https://your-develop-hub-api.onrender.com
const GOOGLE_CLIENT_ID = ""; // Google Web OAuth client ID

const byId = (id) => document.getElementById(id);

let googleIdToken = null;
let currentUser = null;

function showStatus(id, message) {
  const element = byId(id);
  if (element) element.textContent = message;
}

function apiUrl(path) {
  if (!API_BASE_URL) {
    throw new Error("Develop Hub API URL has not been configured.");
  }
  return `${API_BASE_URL.replace(/\/+$/, "")}${path}`;
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (googleIdToken) {
    headers.set("Authorization", `Bearer ${googleIdToken}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), {
    ...options,
    headers
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : { error: `The API returned a non-JSON response (HTTP ${response.status}).` };

  if (!response.ok) {
    throw new Error(data.error || `Request failed: HTTP ${response.status}`);
  }

  return data;
}

async function testApiConnection() {
  showStatus("apiStatus", "Testing…");
  showStatus("healthMessage", "Contacting the Develop Hub API…");

  try {
    const data = await apiFetch("/health");
    showStatus("apiStatus", "Connected");
    showStatus("healthMessage", data.message || data.status || "API is responding.");
  } catch (error) {
    showStatus("apiStatus", "Not connected");
    showStatus("healthMessage", error.message);
  }
}

async function handleGoogleCredential(response) {
  googleIdToken = response.credential;

  try {
    // The backend verifies the Google ID token.
    const data = await apiFetch("/api/me");

    currentUser = data.user;
    showStatus(
      "authStatus",
      `Signed in as ${currentUser.email}${data.is_admin ? " (admin)" : ""}`
    );
    showStatus("adminStatus", data.is_admin ? "Verified admin" : "Not an admin");

    const signInButton = byId("googleSignIn");
    const signOutButton = byId("signOut");

    if (signInButton) signInButton.hidden = true;
    if (signOutButton) signOutButton.hidden = false;

    const uploadForm = byId("apkUploadForm");
    if (uploadForm) uploadForm.hidden = !data.is_admin;

    await loadPublicApps();
  } catch (error) {
    googleIdToken = null;
    currentUser = null;
    showStatus("authStatus", `Sign-in verification failed: ${error.message}`);
    showStatus("adminStatus", "Not verified");
  }
}

function initializeGoogleSignIn() {
  if (!GOOGLE_CLIENT_ID) {
    showStatus("authStatus", "Add your Google Web OAuth client ID to app.js.");
    return;
  }

  if (!window.google?.accounts?.id) {
    showStatus("authStatus", "Google Sign-In library has not loaded.");
    return;
  }

  window.google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleCredential
  });

  const button = byId("googleSignIn");
  if (button) {
    button.addEventListener("click", () => {
      window.google.accounts.id.prompt();
      showStatus("authStatus", "Opening Google Sign-In…");
    });
  }
}

function signOut() {
  googleIdToken = null;
  currentUser = null;

  if (window.google?.accounts?.id) {
    window.google.accounts.id.disableAutoSelect();
  }

  const signInButton = byId("googleSignIn");
  const signOutButton = byId("signOut");

  if (signInButton) signInButton.hidden = false;
  if (signOutButton) signOutButton.hidden = true;

  const uploadForm = byId("apkUploadForm");
  if (uploadForm) uploadForm.hidden = true;

  showStatus("authStatus", "Signed out.");
  showStatus("adminStatus", "Signed out");
}

async function loadPublicApps() {
  const list = byId("appList");
  if (!list) return;

  list.replaceChildren();

  try {
    const data = await apiFetch("/api/apps");

    if (!Array.isArray(data.apps) || data.apps.length === 0) {
      const empty = document.createElement("div");
      empty.className = "stat";

      const title = document.createElement("strong");
      title.textContent = "No published apps yet";

      const description = document.createElement("p");
      description.textContent =
        data.message || "Published applications will appear here.";

      empty.append(title, description);
      list.appendChild(empty);
      return;
    }

    for (const app of data.apps) {
      const card = document.createElement("div");
      card.className = "stat";

      const title = document.createElement("strong");
      title.textContent = app.name || "Android app";

      const description = document.createElement("p");
      description.textContent = app.description || "";

      card.append(title, description);

      // Download links are only rendered when returned by the API.
      if (typeof app.download_url === "string" &&
          app.download_url.startsWith("https://")) {
        const link = document.createElement("a");
        link.className = "button";
        link.href = app.download_url;
        link.textContent = "Download APK";
        link.rel = "noopener";
        card.appendChild(link);
      }

      list.appendChild(card);
    }
  } catch (error) {
    const message = document.createElement("p");
    message.textContent = `Marketplace unavailable: ${error.message}`;
    list.appendChild(message);
  }
}

async function uploadApk(event) {
  event.preventDefault();

  if (!googleIdToken || !currentUser) {
    showStatus("uploadStatus", "Sign in and verify your account first.");
    return;
  }

  const file = byId("apkFile")?.files?.[0];
  if (!file || !file.name.toLowerCase().endsWith(".apk")) {
    showStatus("uploadStatus", "Choose an APK file.");
    return;
  }

  // Upload endpoint and persistent storage must be implemented server-side.
  showStatus(
    "uploadStatus",
    "Upload is not enabled yet. The secure backend upload route must be added first."
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const year = byId("year");
  if (year) year.textContent = new Date().getFullYear();

  byId("testApi")?.addEventListener("click", testApiConnection);
  byId("signOut")?.addEventListener("click", signOut);
  byId("apkUploadForm")?.addEventListener("submit", uploadApk);

  const uploadForm = byId("apkUploadForm");
  if (uploadForm) uploadForm.hidden = true;

  initializeGoogleSignIn();
  loadPublicApps();
});
