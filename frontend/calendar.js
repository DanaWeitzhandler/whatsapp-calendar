const phoneForm = document.getElementById("phone-form");
const phoneInput = document.getElementById("phone-input");
const refreshBtn = document.getElementById("refresh-btn");
const statusEl = document.getElementById("status");
const eventsEl = document.getElementById("events");

let currentPhone = null;

phoneForm.addEventListener("submit", (e) => {
  e.preventDefault();
  currentPhone = phoneInput.value.trim();
  loadEvents();
});

refreshBtn.addEventListener("click", () => {
  loadEvents();
});

async function loadEvents() {
  if (!currentPhone) {
    statusEl.textContent = "Enter a phone number first.";
    return;
  }

  statusEl.textContent = "Loading...";
  try {
    const res = await fetch(`/events?phone=${encodeURIComponent(currentPhone)}`);
    if (!res.ok) throw new Error("Request failed");
    const events = await res.json();
    renderEvents(events);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = "Failed to load events.";
  }
}

function renderEvents(events) {
  eventsEl.innerHTML = "";

  if (events.length === 0) {
    eventsEl.textContent = "No events found.";
    return;
  }

  const byDate = {};
  for (const ev of events) {
    const date = ev.start_time.slice(0, 10);
    if (!byDate[date]) byDate[date] = [];
    byDate[date].push(ev);
  }

  for (const date of Object.keys(byDate).sort()) {
    const heading = document.createElement("h3");
    heading.textContent = date;
    eventsEl.appendChild(heading);

    const list = document.createElement("ul");
    const dayEvents = byDate[date].sort((a, b) => a.start_time.localeCompare(b.start_time));
    for (const ev of dayEvents) {
      const li = document.createElement("li");
      li.className = ev.status === "cancelled" ? "cancelled" : "active";
      const startTime = ev.start_time.slice(11, 16);
      const endTime = ev.end_time.slice(11, 16);
      li.textContent = `${startTime}–${endTime}  ${ev.title}  [${ev.status}]`;
      list.appendChild(li);
    }
    eventsEl.appendChild(list);
  }
}
