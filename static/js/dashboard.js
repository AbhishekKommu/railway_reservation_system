/* dashboard.js — powers the dashboard: tab switching, train search & booking,
   "My Bookings" management (edit/cancel), and the "Manage Trains" CRUD panel.
   All data flows through the /api/* REST endpoints defined in app.py. */

// ---------------------------------------------------------------- Tabs

const tabButtons = document.querySelectorAll(".tab-btn");
tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "bookings") loadBookings();
    if (btn.dataset.tab === "manage") loadManageTrains();
  });
});

// ---------------------------------------------------------------- Search & Book

const trainsList = document.getElementById("trains-list");
const searchForm = document.getElementById("search-form");
document.getElementById("s-date").min = formatDateForInputMin();

async function loadTrains() {
  const source = document.getElementById("s-source").value.trim();
  const destination = document.getElementById("s-destination").value.trim();
  const date = document.getElementById("s-date").value;

  const params = new URLSearchParams();
  if (source) params.set("source", source);
  if (destination) params.set("destination", destination);
  if (date) params.set("date", date);

  trainsList.innerHTML = `<div class="empty-state">Loading trains...</div>`;
  try {
    const trains = await apiRequest(`/api/trains?${params.toString()}`);
    renderTrains(trains, date);
  } catch (err) {
    trainsList.innerHTML = `<div class="empty-state">Failed to load trains.</div>`;
    showToast(err.message, "error");
  }
}

function renderTrains(trains, date) {
  if (trains.length === 0) {
    trainsList.innerHTML = `<div class="empty-state"><div class="icon">🚄</div>No trains match your search.</div>`;
    return;
  }
  trainsList.innerHTML = trains
    .map((t) => {
      const seatsKnown = date !== "";
      const seatsClass = seatsKnown && t.available_seats < 20 ? "seats-low" : "seats-ok";
      const seatsLabel = seatsKnown ? t.available_seats : t.total_seats;
      const seatsCaption = seatsKnown ? "Available" : "Total Seats";
      return `
      <div class="train-card">
        <div class="train-info">
          <h3>${escapeHtml(t.name)} <span style="color:var(--text-muted);font-weight:400;font-size:0.85rem;">#${escapeHtml(t.train_number)}</span></h3>
          <div class="route">${escapeHtml(t.source)} <span class="arrow">&#8594;</span> ${escapeHtml(t.destination)}</div>
        </div>
        <div class="train-meta">
          <div class="item"><div class="label">Departs</div><div class="value">${t.departure_time}</div></div>
          <div class="item"><div class="label">Arrives</div><div class="value">${t.arrival_time}</div></div>
          <div class="item"><div class="label">${seatsCaption}</div><div class="value ${seatsClass}">${seatsLabel}</div></div>
          <div class="item"><div class="label">Fare</div><div class="value fare">&#8377;${t.fare.toFixed(2)}</div></div>
        </div>
        <button class="btn btn-primary btn-sm" onclick="openBookModal(${t.id}, '${escapeHtml(t.name).replace(/'/g, "\\'")}', '${escapeHtml(t.train_number)}')">Book</button>
      </div>`;
    })
    .join("");
}

searchForm.addEventListener("submit", (e) => {
  e.preventDefault();
  loadTrains();
});

// ---------------------------------------------------------------- Book modal

let selectedTrainId = null;
const bookModal = document.getElementById("book-modal-overlay");
document.getElementById("book-date").min = formatDateForInputMin();

function openBookModal(trainId, name, number) {
  selectedTrainId = trainId;
  document.getElementById("book-train-label").value = `${name} (#${number})`;
  document.getElementById("book-date").value = document.getElementById("s-date").value || "";
  document.getElementById("book-seats").value = 1;
  bookModal.classList.add("show");
}

document.getElementById("book-cancel-btn").addEventListener("click", () => bookModal.classList.remove("show"));

document.getElementById("book-confirm-btn").addEventListener("click", async () => {
  const journey_date = document.getElementById("book-date").value;
  const seats = parseInt(document.getElementById("book-seats").value, 10);
  if (!journey_date || !seats || seats < 1) {
    showToast("Please choose a date and a valid number of seats.", "error");
    return;
  }
  try {
    const booking = await apiRequest("/api/bookings", {
      method: "POST",
      body: { train_id: selectedTrainId, journey_date, seats },
    });
    bookModal.classList.remove("show");
    showToast(`Booked! Your PNR is ${booking.pnr}`, "success");
    loadTrains();
  } catch (err) {
    showToast(err.message, "error");
  }
});

// ---------------------------------------------------------------- My Bookings

const bookingsList = document.getElementById("bookings-list");

async function loadBookings() {
  bookingsList.innerHTML = `<div class="empty-state">Loading your bookings...</div>`;
  try {
    const bookings = await apiRequest("/api/bookings");
    renderBookings(bookings);
  } catch (err) {
    bookingsList.innerHTML = `<div class="empty-state">Failed to load bookings.</div>`;
  }
}

function renderBookings(bookings) {
  if (bookings.length === 0) {
    bookingsList.innerHTML = `<div class="empty-state"><div class="icon">🎫</div>You haven't booked any tickets yet.</div>`;
    return;
  }
  bookingsList.innerHTML = bookings
    .map((b) => {
      const badgeClass = b.status === "CONFIRMED" ? "confirmed" : "cancelled";
      const actions =
        b.status === "CONFIRMED"
          ? `<button class="btn btn-ghost btn-sm" onclick="openEditModal(${b.id}, '${b.journey_date}', ${b.seats})">Edit</button>
             <button class="btn btn-danger btn-sm" onclick="cancelBooking(${b.id})">Cancel</button>`
          : "";
      return `
      <div class="booking-card">
        <div class="train-info">
          <h3>${escapeHtml(b.train_name)} <span style="color:var(--text-muted);font-weight:400;font-size:0.85rem;">#${escapeHtml(b.train_number)}</span></h3>
          <div class="route">${escapeHtml(b.source)} <span class="arrow">&#8594;</span> ${escapeHtml(b.destination)} &nbsp;|&nbsp; PNR: ${escapeHtml(b.pnr)}</div>
        </div>
        <div class="train-meta">
          <div class="item"><div class="label">Date</div><div class="value">${b.journey_date}</div></div>
          <div class="item"><div class="label">Seats</div><div class="value">${b.seats}</div></div>
          <div class="item"><div class="label">Total Fare</div><div class="value fare">&#8377;${b.total_fare.toFixed(2)}</div></div>
          <div class="item"><div class="label">Status</div><div class="badge ${badgeClass}">${b.status}</div></div>
        </div>
        <div style="display:flex; gap:8px;">${actions}</div>
      </div>`;
    })
    .join("");
}

async function cancelBooking(id) {
  if (!confirm("Cancel this booking?")) return;
  try {
    await apiRequest(`/api/bookings/${id}`, { method: "DELETE" });
    showToast("Booking cancelled.", "success");
    loadBookings();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------- Edit booking modal

let editingBookingId = null;
const editModal = document.getElementById("edit-modal-overlay");
document.getElementById("edit-date").min = formatDateForInputMin();

function openEditModal(id, date, seats) {
  editingBookingId = id;
  document.getElementById("edit-date").value = date;
  document.getElementById("edit-seats").value = seats;
  editModal.classList.add("show");
}

document.getElementById("edit-cancel-btn").addEventListener("click", () => editModal.classList.remove("show"));

document.getElementById("edit-confirm-btn").addEventListener("click", async () => {
  const journey_date = document.getElementById("edit-date").value;
  const seats = parseInt(document.getElementById("edit-seats").value, 10);
  try {
    await apiRequest(`/api/bookings/${editingBookingId}`, {
      method: "PUT",
      body: { journey_date, seats },
    });
    editModal.classList.remove("show");
    showToast("Booking updated.", "success");
    loadBookings();
  } catch (err) {
    showToast(err.message, "error");
  }
});

// ---------------------------------------------------------------- Manage Trains (CRUD)

const manageList = document.getElementById("manage-list");
const addTrainForm = document.getElementById("add-train-form");
let editingTrainId = null;

async function loadManageTrains() {
  manageList.innerHTML = `<div class="empty-state">Loading trains...</div>`;
  try {
    const trains = await apiRequest("/api/trains");
    renderManageTrains(trains);
  } catch (err) {
    manageList.innerHTML = `<div class="empty-state">Failed to load trains.</div>`;
  }
}

function renderManageTrains(trains) {
  if (trains.length === 0) {
    manageList.innerHTML = `<div class="empty-state">No trains yet. Add one above.</div>`;
    return;
  }
  manageList.innerHTML = trains
    .map(
      (t) => `
      <div class="train-card">
        <div class="train-info">
          <h3>${escapeHtml(t.name)} <span style="color:var(--text-muted);font-weight:400;font-size:0.85rem;">#${escapeHtml(t.train_number)}</span></h3>
          <div class="route">${escapeHtml(t.source)} <span class="arrow">&#8594;</span> ${escapeHtml(t.destination)}</div>
        </div>
        <div class="train-meta">
          <div class="item"><div class="label">Departs</div><div class="value">${t.departure_time}</div></div>
          <div class="item"><div class="label">Arrives</div><div class="value">${t.arrival_time}</div></div>
          <div class="item"><div class="label">Seats</div><div class="value">${t.total_seats}</div></div>
          <div class="item"><div class="label">Fare</div><div class="value fare">&#8377;${t.fare.toFixed(2)}</div></div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-ghost btn-sm" onclick='fillTrainForm(${JSON.stringify(t)})'>Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTrain(${t.id})">Delete</button>
        </div>
      </div>`
    )
    .join("");
}

function fillTrainForm(t) {
  editingTrainId = t.id;
  document.getElementById("t-number").value = t.train_number;
  document.getElementById("t-name").value = t.name;
  document.getElementById("t-source").value = t.source;
  document.getElementById("t-destination").value = t.destination;
  document.getElementById("t-departure").value = t.departure_time;
  document.getElementById("t-arrival").value = t.arrival_time;
  document.getElementById("t-seats").value = t.total_seats;
  document.getElementById("t-fare").value = t.fare;
  addTrainForm.querySelector("button[type=submit]").textContent = "Update Train";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetTrainForm() {
  editingTrainId = null;
  addTrainForm.reset();
  addTrainForm.querySelector("button[type=submit]").textContent = "Add Train";
}

addTrainForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    train_number: document.getElementById("t-number").value.trim(),
    name: document.getElementById("t-name").value.trim(),
    source: document.getElementById("t-source").value.trim(),
    destination: document.getElementById("t-destination").value.trim(),
    departure_time: document.getElementById("t-departure").value,
    arrival_time: document.getElementById("t-arrival").value,
    total_seats: parseInt(document.getElementById("t-seats").value, 10),
    fare: parseFloat(document.getElementById("t-fare").value),
  };

  try {
    if (editingTrainId) {
      await apiRequest(`/api/trains/${editingTrainId}`, { method: "PUT", body: payload });
      showToast("Train updated.", "success");
    } else {
      await apiRequest("/api/trains", { method: "POST", body: payload });
      showToast("Train added.", "success");
    }
    resetTrainForm();
    loadManageTrains();
  } catch (err) {
    showToast(err.message, "error");
  }
});

async function deleteTrain(id) {
  if (!confirm("Delete this train? Existing bookings referencing it will also be removed.")) return;
  try {
    await apiRequest(`/api/trains/${id}`, { method: "DELETE" });
    showToast("Train deleted.", "success");
    loadManageTrains();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------- Utils

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------------------------------------------------------------- Init

loadTrains();
