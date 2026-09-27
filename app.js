/*
 * SOV DEV HUB
 * Frontend V1
 *
 * The upload form currently demonstrates the interface.
 * Real APK storage should be connected to the backend before
 * accepting public uploads.
 */


const apps = [

  {
    name: "Scorpio Octavious Vibe",
    description: "Social, rewards, wallet and entertainment platform.",
    category: "Social",
    version: "1.0.0",
    icon: "🦂"
  },

  {
    name: "SOV Wallet",
    description: "Manage SOV balances, transfers and transactions.",
    category: "Finance",
    version: "1.0.0",
    icon: "💰"
  },

  {
    name: "SOV Games",
    description: "Discover games and entertainment experiences.",
    category: "Games",
    version: "1.0.0",
    icon: "🎮"
  },

  {
    name: "SOV Connect",
    description: "Connect with people and discover communities.",
    category: "Social",
    version: "1.0.0",
    icon: "👥"
  }

];


let currentCategory = "All";


document.addEventListener("DOMContentLoaded", () => {

  renderApps(apps);

  updateAppCount();

});


function renderApps(list) {

  const grid = document.getElementById("appGrid");

  if (!grid) return;

  grid.innerHTML = "";


  if (list.length === 0) {

    grid.innerHTML = `
      <div style="
        grid-column: 1/-1;
        padding: 50px;
        text-align: center;
        color: #8994a8;
      ">
        No apps found.
      </div>
    `;

    return;
  }


  list.forEach(app => {

    const card = document.createElement("div");

    card.className = "app-card";

    card.innerHTML = `

      <div class="app-icon">
        ${app.icon || "📱"}
      </div>

      <h3>
        ${escapeHTML(app.name)}
      </h3>

      <p>
        ${escapeHTML(app.description)}
      </p>

      <div class="app-meta">
        ${escapeHTML(app.category)}
        • Version ${escapeHTML(app.version)}
      </div>

      <button
        class="app-download"
        onclick="viewApp('${escapeHTML(app.name)}')"
      >
        View App
      </button>

    `;

    grid.appendChild(card);

  });

}


function filterCategory(category) {

  currentCategory = category;

  if (category === "All") {

    renderApps(apps);

    return;
  }


  const filtered = apps.filter(
    app => app.category === category
  );

  renderApps(filtered);

  document
    .getElementById("apps")
    .scrollIntoView({
      behavior: "smooth"
    });

}


function searchApps() {

  const query =
    document
      .getElementById("searchInput")
      .value
      .toLowerCase()
      .trim();


  let filtered = apps;


  if (currentCategory !== "All") {

    filtered = filtered.filter(
      app => app.category === currentCategory
    );

  }


  if (query) {

    filtered = filtered.filter(app =>

      app.name.toLowerCase().includes(query) ||

      app.description.toLowerCase().includes(query) ||

      app.category.toLowerCase().includes(query)

    );

  }


  renderApps(filtered);

}


function updateAppCount() {

  document.getElementById("appCount").textContent =
    apps.length;

}


function openDeveloper() {

  document
    .getElementById("developerModal")
    .classList.add("show");

  document.body.style.overflow = "hidden";

}


function closeDeveloper() {

  document
    .getElementById("developerModal")
    .classList.remove("show");

  document.body.style.overflow = "";

}


function scrollToApps() {

  document
    .getElementById("apps")
    .scrollIntoView({
      behavior: "smooth"
    });

}


function viewApp(name) {

  alert(
    "App details page for " +
    name +
    " will be connected in the next version."
  );

}


/*
 * Demo submission
 */

document
  .getElementById("uploadForm")
  .addEventListener("submit", function(event) {

    event.preventDefault();


    const apk =
      document.getElementById("apkFile").files[0];


    if (!apk) {

      showUploadMessage(
        "Please select an APK file."
      );

      return;

    }


    if (!apk.name.toLowerCase().endsWith(".apk")) {

      showUploadMessage(
        "Only APK files are allowed."
      );

      return;

    }


    const appName =
      document.getElementById("appName").value;


    showUploadMessage(
      "✓ " +
      appName +
      " has been submitted for review."
    );


    /*
     * IMPORTANT:
     *
     * This demo does NOT upload the APK anywhere.
     *
     * In the production version this form will send
     * the APK to the SOV backend using multipart/form-data.
     */


});


function showUploadMessage(message) {

  document.getElementById(
    "uploadMessage"
  ).textContent = message;

}


/*
 * Basic HTML escaping for displayed text.
 */

function escapeHTML(value) {

  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

}


/*
 * Close modal when clicking outside the card.
 */

document
  .getElementById("developerModal")
  .addEventListener("click", function(event) {

    if (event.target === this) {

      closeDeveloper();

    }

  });
