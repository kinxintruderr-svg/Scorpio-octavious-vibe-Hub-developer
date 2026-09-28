/*
=========================================================
SOV DEV HUB — REAL FRONTEND
=========================================================

This frontend connects to the Flask API.

IMPORTANT:
Change API_BASE to your deployed backend URL.

Example:

https://your-sov-dev-hub-api.onrender.com

Do NOT put secret admin keys in this file.
=========================================================
*/


const API_BASE =
  localStorage.getItem("sov_api_url") ||
  "http://localhost:5000";


let currentCategory = "";

let currentApps = [];



/* ======================================================
   START
====================================================== */

document.addEventListener(
  "DOMContentLoaded",
  () => {

    setupEvents();

    updateNavigation();

    loadApps();

  }
);



/* ======================================================
   EVENTS
====================================================== */

function setupEvents() {

  document
    .getElementById("searchInput")
    .addEventListener(
      "input",
      loadApps
    );


  document
    .querySelectorAll(".category")
    .forEach(button => {

      button.addEventListener(
        "click",
        () => {

          document
            .querySelectorAll(".category")
            .forEach(item =>
              item.classList.remove("active")
            );


          button.classList.add("active");


          currentCategory =
            button.dataset.category || "";


          loadApps();

        }
      );

    });


  document
    .getElementById("loginForm")
    .addEventListener(
      "submit",
      login
    );


  document
    .getElementById("registerForm")
    .addEventListener(
      "submit",
      register
    );


  document
    .getElementById("uploadForm")
    .addEventListener(
      "submit",
      uploadApp
    );


  window.addEventListener(
    "click",
    event => {

      if (
        event.target.classList.contains("modal")
      ) {

        event.target.classList.remove(
          "show"
        );

      }

    }
  );

}



/* ======================================================
   API REQUEST
====================================================== */

async function api(
  endpoint,
  options = {}
) {

  const response =
    await fetch(
      API_BASE + endpoint,
      options
    );


  let data;


  try {

    data =
      await response.json();

  } catch {

    data = {
      success: false,
      error: "Invalid server response"
    };

  }


  if (!response.ok) {

    throw new Error(
      data.error ||
      "Request failed"
    );

  }


  return data;

}



/* ======================================================
   LOAD PUBLIC APPS
====================================================== */

async function loadApps() {

  const grid =
    document.getElementById(
      "appGrid"
    );


  const status =
    document.getElementById(
      "appStatus"
    );


  grid.innerHTML = `
    <div class="loading">
      Loading apps...
    </div>
  `;


  const search =
    document
      .getElementById(
        "searchInput"
      )
      .value
      .trim();


  try {

    const params =
      new URLSearchParams();


    if (search) {

      params.set(
        "search",
        search
      );

    }


    if (currentCategory) {

      params.set(
        "category",
        currentCategory
      );

    }


    const query =
      params.toString()
        ? "?" + params.toString()
        : "";


    const data =
      await api(
        "/api/apps" + query
      );


    currentApps =
      data.apps || [];


    renderApps(
      currentApps
    );


    status.textContent =
      currentApps.length +
      " app" +
      (
        currentApps.length === 1
          ? ""
          : "s"
      );



    updatePublicStats(
      currentApps
    );


  } catch (error) {

    grid.innerHTML = `
      <div class="empty-state">
        <strong>Unable to load apps</strong>
        <p>
          ${escapeHTML(error.message)}
        </p>
      </div>
    `;

    status.textContent =
      "Connection error";

  }

}



/* ======================================================
   RENDER APPS
====================================================== */

function renderApps(apps) {

  const grid =
    document.getElementById(
      "appGrid"
    );


  if (!apps.length) {

    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📱</div>

        <strong>
          No published apps yet
        </strong>

        <p>
          Approved applications will appear here.
        </p>
      </div>
    `;

    return;

  }


  grid.innerHTML =
    apps.map(
      app => {

        const icon =
          app.icon
            ? API_BASE + app.icon
            : "";


        return `

          <article class="app-card">

            <div class="app-card-top">

              ${
                icon

                ? `
                  <img
                    class="app-icon"
                    src="${escapeAttribute(icon)}"
                    alt=""
                  >
                `

                : `
                  <div class="app-icon placeholder">
                    📱
                  </div>
                `
              }

              <div class="app-card-title">

                <h3>
                  ${escapeHTML(app.name)}
                </h3>

                <span>
                  ${escapeHTML(app.category)}
                </span>

              </div>

            </div>


            <p class="app-description">
              ${escapeHTML(app.description)}
            </p>


            <div class="app-meta">

              <span>
                v${escapeHTML(app.version)}
              </span>

              <span>
                ↓ ${Number(app.downloads || 0).toLocaleString()}
              </span>

            </div>


            <button
              class="app-button"
              onclick="openAppDetails(${Number(app.id)})"
            >
              View App
            </button>

          </article>

        `;

      }
    ).join("");

}



/* ======================================================
   PUBLIC STATS
====================================================== */

function updatePublicStats(apps) {

  const count =
    apps.length;


  const downloads =
    apps.reduce(
      (
        total,
        app
      ) =>
        total +
        Number(
          app.downloads || 0
        ),
      0
    );


  document.getElementById(
    "totalApps"
  ).textContent =
    count.toLocaleString();


  document.getElementById(
    "totalDownloads"
  ).textContent =
    downloads.toLocaleString();

}



/* ======================================================
   APP DETAILS
====================================================== */

async function openAppDetails(
  appId
) {

  const container =
    document.getElementById(
      "appDetails"
    );


  container.innerHTML = `
    <div class="loading">
      Loading application...
    </div>
  `;


  document
    .getElementById(
      "appModal"
    )
    .classList.add("show");


  try {

    const data =
      await api(
        "/api/apps/" +
        encodeURIComponent(
          appId
        )
      );


    const app =
      data.app;


    const icon =
      app.icon
        ? API_BASE + app.icon
        : "";


    container.innerHTML = `

      <div class="detail-icon">

        ${
          icon

          ? `
            <img
              src="${escapeAttribute(icon)}"
              alt=""
            >
          `

          : "📱"
        }

      </div>


      <small>
        ${escapeHTML(app.category)}
      </small>


      <h2>
        ${escapeHTML(app.name)}
      </h2>


      <p class="detail-developer">
        Developed by
        <strong>
          ${escapeHTML(
            app.developer_name ||
            app.developer
          )}
        </strong>
      </p>


      <p class="detail-description">
        ${escapeHTML(
          app.description
        )}
      </p>


      <div class="detail-info">

        <div>
          <span>Version</span>
          <strong>
            ${escapeHTML(app.version)}
          </strong>
        </div>

        <div>
          <span>Downloads</span>
          <strong>
            ${Number(
              app.downloads || 0
            ).toLocaleString()}
          </strong>
        </div>

      </div>


      <a
        class="primary-button download-link"
        href="${
          API_BASE
        }/api/apps/${
          Number(app.id)
        }/download"
      >
        Download APK
      </a>

    `;


  } catch (error) {

    container.innerHTML = `

      <div class="empty-state">

        <strong>
          Unable to load app
        </strong>

        <p>
          ${escapeHTML(error.message)}
        </p>

      </div>

    `;

  }

}



function closeAppDetails() {

  document
    .getElementById(
      "appModal"
    )
    .classList.remove(
      "show"
    );

}



/* ======================================================
   REGISTER
====================================================== */

async function register(
  event
) {

  event.preventDefault();


  const message =
    document.getElementById(
      "authMessage"
    );


  message.textContent =
    "Creating account...";


  try {

    const data =
      await api(
        "/api/developers/register",
        {

          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({

            username:
              document.getElementById(
                "registerUsername"
              ).value.trim(),

            display_name:
              document.getElementById(
                "registerDisplayName"
              ).value.trim(),

            email:
              document.getElementById(
                "registerEmail"
              ).value.trim(),

            password:
              document.getElementById(
                "registerPassword"
              ).value

          })

        }
      );


    saveSession(
      data.token,
      data.developer
    );


    closeAuth();

    updateNavigation();

    showDashboard();

    showToast(
      "Developer account created."
    );


    document
      .getElementById(
        "registerForm"
      )
      .reset();


  } catch (error) {

    message.textContent =
      error.message;

  }

}



/* ======================================================
   LOGIN
====================================================== */

async function login(
  event
) {

  event.preventDefault();


  const message =
    document.getElementById(
      "authMessage"
    );


  message.textContent =
    "Signing in...";


  try {

    const data =
      await api(
        "/api/developers/login",
        {

          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({

            username_or_email:
              document.getElementById(
                "loginUsername"
              ).value.trim(),

            password:
              document.getElementById(
                "loginPassword"
              ).value

          })

        }
      );


    saveSession(
      data.token,
      data.developer
    );


    closeAuth();

    updateNavigation();

    showDashboard();

    showToast(
      "Welcome back."
    );


    document
      .getElementById(
        "loginForm"
      )
      .reset();


  } catch (error) {

    message.textContent =
      error.message;

  }

}



/* ======================================================
   SESSION
====================================================== */

function saveSession(
  token,
  developer
) {

  localStorage.setItem(
    "sov_dev_token",
    token
  );


  localStorage.setItem(
    "sov_dev_user",
    JSON.stringify(
      developer
    )
  );

}



function getToken() {

  return localStorage.getItem(
    "sov_dev_token"
  );

}



function getUser() {

  try {

    return JSON.parse(
      localStorage.getItem(
        "sov_dev_user"
      )
    );

  } catch {

    return null;

  }

}



function logout() {

  localStorage.removeItem(
    "sov_dev_token"
  );

  localStorage.removeItem(
    "sov_dev_user"
  );


  updateNavigation();


  document
    .getElementById(
      "dashboard"
    )
    .classList.add(
      "hidden"
    );


  showToast(
    "You have been logged out."
  );

}



/* ======================================================
   NAVIGATION
====================================================== */

function updateNavigation() {

  const loggedIn =
    Boolean(
      getToken()
    );


  document
    .getElementById(
      "loginNavButton"
    )
    .classList.toggle(
      "hidden",
      loggedIn
    );


  document
    .getElementById(
      "dashboardNavButton"
    )
    .classList.toggle(
      "hidden",
      !loggedIn
    );


  document
    .getElementById(
      "logoutNavButton"
    )
    .classList.toggle(
      "hidden",
      !loggedIn
    );

}



/* ======================================================
   DASHBOARD
====================================================== */

async function showDashboard() {

  if (!getToken()) {

    openAuth(
      "login"
    );

    return;

  }


  const dashboard =
    document.getElementById(
      "dashboard"
    );


  dashboard.classList.remove(
    "hidden"
  );


  dashboard.scrollIntoView({
    behavior: "smooth"
  });


  const user =
    getUser();


  document.getElementById(
    "developerWelcome"
  ).textContent =
    user
      ? "Welcome, " +
        user.display_name
      : "";


  await loadMyApps();

}



/* ======================================================
   MY APPS
====================================================== */

async function loadMyApps() {

  const grid =
    document.getElementById(
      "myAppsGrid"
    );


  grid.innerHTML = `
    <div class="loading">
      Loading your applications...
    </div>
  `;


  try {

    const data =
      await api(
        "/api/developers/my-apps",
        {

          headers: {
            Authorization:
              "Bearer " +
              getToken()
          }

        }
      );


    const apps =
      data.apps || [];


    document.getElementById(
      "myAppCount"
    ).textContent =
      apps.length.toLocaleString();


    const downloads =
      apps.reduce(
        (
          total,
          app
        ) =>
          total +
          Number(
            app.downloads || 0
          ),
        0
      );


    document.getElementById(
      "myDownloadCount"
    ).textContent =
      downloads.toLocaleString();


    if (!apps.length) {

      grid.innerHTML = `

        <div class="empty-state">

          <div class="empty-icon">
            📱
          </div>

          <strong>
            You haven't uploaded an app yet.
          </strong>

          <p>
            Upload your first APK to get started.
          </p>

          <button
            class="primary-button"
            onclick="openUpload()"
          >
            Upload App
          </button>

        </div>

      `;

      return;

    }


    grid.innerHTML =
      apps.map(
        app => `

          <div class="my-app-card">

            <div>

              <h3>
                ${escapeHTML(app.name)}
              </h3>

              <p>
                v${escapeHTML(app.version)}
                •
                ${escapeHTML(app.category)}
              </p>

            </div>


            <span
              class="status status-${escapeAttribute(
                app.status
              )}"
            >
              ${escapeHTML(
                app.status
              )}
            </span>


            <div class="my-app-bottom">

              <span>
                ↓ ${Number(
                  app.downloads || 0
                ).toLocaleString()}
              </span>

              <span>
                ${formatDate(
                  app.updated_at
                )}
              </span>

            </div>

          </div>

        `
      ).join("");


  } catch (error) {

    grid.innerHTML = `

      <div class="empty-state">

        <strong>
          Could not load your apps
        </strong>

        <p>
          ${escapeHTML(error.message)}
        </p>

      </div>

    `;

  }

}



/* ======================================================
   UPLOAD APP
====================================================== */

async function uploadApp(
  event
) {

  event.preventDefault();


  if (!getToken()) {

    closeUpload();

    openAuth(
      "login"
    );

    return;

  }


  const submit =
    document.getElementById(
      "uploadSubmit"
    );


  const message =
    document.getElementById(
      "uploadMessage"
    );


  const apk =
    document.getElementById(
      "uploadApk"
    ).files[0];


  if (!apk) {

    message.textContent =
      "Please select an APK.";

    return;

  }


  if (
    !apk.name
      .toLowerCase()
      .endsWith(".apk")
  ) {

    message.textContent =
      "Only APK files are allowed.";

    return;

  }


  if (
    apk.size >
    200 * 1024 * 1024
  ) {

    message.textContent =
      "APK must be smaller than 200 MB.";

    return;

  }


  const form =
    new FormData();


  form.append(
    "name",
    document.getElementById(
      "uploadName"
    ).value.trim()
  );


  form.append(
    "description",
    document.getElementById(
      "uploadDescription"
    ).value.trim()
  );


  form.append(
    "category",
    document.getElementById(
      "uploadCategory"
    ).value
  );


  form.append(
    "version",
    document.getElementById(
      "uploadVersion"
    ).value.trim()
  );


  form.append(
    "apk",
    apk
  );


  const icon =
    document.getElementById(
      "uploadIcon"
    ).files[0];


  if (icon) {

    form.append(
      "icon",
      icon
    );

  }


  submit.disabled =
    true;


  submit.textContent =
    "Uploading...";


  message.textContent =
    "Uploading APK. Please wait...";


  try {

    const data =
      await api(
        "/api/apps",
        {

          method: "POST",

          headers: {
            Authorization:
              "Bearer " +
              getToken()
          },

          body: form

        }
      );


    message.textContent =
      "✓ " +
      data.message;


    document
      .getElementById(
        "uploadForm"
      )
      .reset();


    await loadMyApps();


    showToast(
      "App submitted for review."
    );


    setTimeout(
      closeUpload,
      1500
    );


  } catch (error) {

    message.textContent =
      error.message;

  } finally {

    submit.disabled =
      false;

    submit.textContent =
      "Submit App For Review";

  }

}



/* ======================================================
   AUTH UI
====================================================== */

function openAuth(
  mode = "login"
) {

  document
    .getElementById(
      "authModal"
    )
    .classList.add(
      "show"
    );


  switchAuth(
    mode
  );

}



function closeAuth() {

  document
    .getElementById(
      "authModal"
    )
    .classList.remove(
      "show"
    );


  document.getElementById(
    "authMessage"
  ).textContent = "";

}



function switchAuth(
  mode
) {

  const loginPanel =
    document.getElementById(
      "loginPanel"
    );


  const registerPanel =
    document.getElementById(
      "registerPanel"
    );


  loginPanel.classList.toggle(
    "hidden",
    mode !== "login"
  );


  registerPanel.classList.toggle(
    "hidden",
    mode !== "register"
  );


  document.getElementById(
    "authMessage"
  ).textContent = "";

}



/* ======================================================
   UPLOAD UI
======================================================*/

function openUpload() {

  if (!getToken()) {

    openAuth(
      "login"
    );

    return;

  }


  document
    .getElementById(
      "uploadModal"
    )
    .classList.add(
      "show"
    );

}



function closeUpload() {

  document
    .getElementById(
      "uploadModal"
    )
    .classList.remove(
      "show"
    );

}



/* ======================================================
   UTILITIES
====================================================== */

function scrollToApps() {

  document
    .getElementById(
      "apps"
    )
    .scrollIntoView({
      behavior: "smooth"
    });

}



function showToast(
  message
) {

  const toast =
    document.getElementById(
      "toast"
    );


  toast.textContent =
    message;


  toast.classList.add(
    "show"
  );


  setTimeout(
    () => {

      toast.classList.remove(
        "show"
      );

    },
    3000
  );

}



function formatDate(
  value
) {

  if (!value) {

    return "";

  }


  const date =
    new Date(
      value
    );


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return "";

  }


  return date.toLocaleDateString();

}



function escapeHTML(
  value
) {

  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    )
    .replaceAll(
      "'",
      "&#039;"
    );

}



function escapeAttribute(
  value
) {

  return escapeHTML(
    value
  );

}