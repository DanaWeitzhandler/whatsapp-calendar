# WhatsApp Calendar Bot (MVP)

A minimal calendar app managed entirely through natural-language WhatsApp
messages. A user texts a real WhatsApp number (via Twilio's WhatsApp
Sandbox), an LLM (Gemini) turns the message into a structured calendar
action, the app applies it to SQLite, and the result is visible in a
browser calendar after a refresh.

## Architecture flow

```
WhatsApp user
  → Twilio WhatsApp Sandbox
  → POST /webhook (FastAPI, public HTTPS via Railway)
  → whatsapp.py: parse sender phone + message text
  → db.py: load that phone's last_event_id (+ that event's details, if any)
  → llm.py: Gemini interprets the message into one structured action
            {create | update | cancel | clarify}
  → db.py: validate + apply the action to SQLite (ownership-checked)
  → whatsapp.py: build a TwiML confirmation reply
  → Twilio delivers the reply back to the same WhatsApp user

Browser
  → GET /            (FastAPI serves frontend/ as static files)
  → user enters their WhatsApp phone number (E.164)
  → GET /events?phone=...
  → SQLite → JSON
  → calendar.js renders events grouped by date (refresh to see updates)
```

The LLM never touches the database directly — it only returns a structured
action. All validation and every SQLite write happen in application code.

## Technologies used

- **FastAPI** — webhook + API + static frontend host, single process
- **SQLite** — one file, two tables (`events`, `conversation_state`)
- **Gemini API** (`google-genai`, `gemini-flash-lite-latest`) — natural-language → structured JSON action, via a Pydantic response schema
- **Twilio WhatsApp Sandbox** — real WhatsApp connection, no production WhatsApp Business approval needed for an MVP
- **Railway** — public HTTPS hosting with a persistent volume for the SQLite file
- Plain **HTML / CSS / JavaScript** frontend — no framework, no build step

## How to test the WhatsApp bot

1. From a real WhatsApp account, send the Twilio Sandbox's join code to the Sandbox number (Twilio Console → Messaging → Try it out → WhatsApp Sandbox).
2. Send a message such as:
   `Schedule a meeting with Shani the day after tomorrow at 16:00 for one hour.`
   The bot replies confirming the created event.
3. Send a follow-up using an implicit reference to the same event:
   `Move it to 17:00.` → the bot updates that event and confirms.
4. Send:
   `The meeting was cancelled.` → the bot cancels that event and confirms.
5. Send a message naming an event that isn't the last relevant one (e.g. `Cancel my dentist appointment` when it isn't) — the bot asks for clarification instead of guessing, and nothing changes in the database.

## How to open the deployed calendar

1. Open the Railway HTTPS URL in a browser.
2. Enter the WhatsApp phone number you used to message the bot, in E.164 format (e.g. `+972501234567`, no `whatsapp:` prefix).
3. Click **Load events** to see that phone's events grouped by date.
4. After sending a new WhatsApp message, click **Refresh** to see the change — updates are refresh-based, not real-time (no WebSockets).

## Key design decisions

- **Context = `last_event_id` only.** Each phone number's conversation context is a single field: the id of its most recently relevant event. This is enough to resolve pronoun-style follow-ups ("move it", "cancel it"). If a message names a different event that doesn't match, the LLM is instructed to return `clarify` rather than guess — searching across all of a user's events by name is explicitly out of scope for this MVP.
- **LLM produces structure, not side effects.** Gemini returns one of `create` / `update` / `cancel` / `clarify` via a JSON schema (Pydantic model), with `temperature=0` for consistent date/time interpretation. Application code is the only thing that writes to SQLite.
- **Ownership enforced in SQL, not just in application logic.** `update_event`/`cancel_event` scope their `UPDATE` by `id AND phone` together, so one phone number can never modify another phone's event even if the app layer had a bug.
- **Synchronous TwiML replies.** The webhook responds to Twilio's POST directly with a TwiML `<Message>` — no Twilio REST client, no Account SID/Auth Token, and no background worker/queue is possible by construction, since the whole request is handled in one synchronous pass.
- **Soft deletes.** Cancelling sets `status = 'cancelled'`; rows are never deleted. The calendar shows cancelled events struck through instead of hiding them.
- **Refresh-based calendar.** Per the MVP scope, the browser calendar is a simple fetch-on-demand view, not a live/streaming one.

## MVP limitations

- **No real authentication.** Anyone who knows or guesses a phone number can view that phone's calendar in the browser — there's no login, just a phone-number text field.
- **Context is single-event only.** Referencing an older event by name (when it isn't the current `last_event_id`) isn't resolved automatically; the bot asks for clarification instead.
- **Twilio Sandbox, not a production WhatsApp sender.** Sandbox membership expires after 3 days and testers must rejoin; this is not a Twilio-approved WhatsApp Business number.
- **Single instance, single-writer SQLite.** The Railway service intentionally runs as one instance because SQLite on a mounted volume doesn't support concurrent multi-instance writes.
- **No recurring events, reminders, or per-user timezones** — all times are interpreted in Asia/Jerusalem.

## What I would improve next

- Real authentication (e.g. WhatsApp-verified login) instead of a typed phone number.
- Broader event resolution — let the LLM (or app code) search a user's events by title/date, not just the last relevant one.
- Move to a networked database if scaling beyond a single instance is ever needed.
- Real-time calendar updates (WebSockets or polling) instead of manual refresh.
- Move off the Twilio Sandbox to an approved WhatsApp Business sender for real users.

## Project structure

```
main.py       FastAPI app: startup, /webhook, /events, serves frontend/
db.py         All SQLite operations (events, conversation_state)
llm.py        Gemini call: message → structured action (no DB access)
whatsapp.py   Twilio webhook parsing + TwiML reply building
frontend/     index.html, calendar.js, styles.css (no framework)
```

## Environment variables

See `.env.example`:

- `GEMINI_API_KEY` — Gemini API key
- `DB_PATH` — path to the SQLite file (`./app.db` locally, a path on the mounted persistent volume, e.g. `/data/app.db`, on Railway)
