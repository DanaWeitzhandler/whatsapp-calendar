from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

import db
import llm
import whatsapp

app = FastAPI()


@app.on_event("startup")
def startup():
    db.init_db()


def _format_dt(iso_str):
    return datetime.fromisoformat(iso_str).strftime("%B %d at %H:%M")


def _handle_create(phone, action):
    event_id = db.create_event(phone, action["title"], action["start_time"], action["end_time"])
    db.set_last_event_id(phone, event_id)
    return f"'{action['title']}' was scheduled for {_format_dt(action['start_time'])}."


def _handle_update(phone, action):
    event_id = action["event_id"]
    if event_id is None:
        return "Sorry, I couldn't tell which event to update. Could you clarify?"

    event = db.get_event(event_id)
    title = action.get("title") or (event["title"] if event else "your event")

    success = db.update_event(
        event_id,
        phone,
        title=action.get("title"),
        start_time=action.get("start_time"),
        end_time=action.get("end_time"),
    )
    if not success:
        return "Sorry, I couldn't find that event to update."

    db.set_last_event_id(phone, event_id)
    if action.get("start_time"):
        return f"'{title}' was updated to {_format_dt(action['start_time'])}."
    return f"'{title}' was updated."


def _handle_cancel(phone, action):
    event_id = action["event_id"]
    if event_id is None:
        return "Sorry, I couldn't tell which event to cancel. Could you clarify?"

    event = db.get_event(event_id)
    title = event["title"] if event else "your event"

    success = db.cancel_event(event_id, phone)
    if not success:
        return "Sorry, I couldn't find that event to cancel."

    return f"'{title}' was cancelled."


def _handle_clarify(action):
    return action.get("reply_text") or "Sorry, I didn't understand that. Could you rephrase?"


def handle_action(phone, action):
    act = action.get("action")
    if act == "create":
        return _handle_create(phone, action)
    if act == "update":
        return _handle_update(phone, action)
    if act == "cancel":
        return _handle_cancel(phone, action)
    if act == "clarify":
        return _handle_clarify(action)
    return "Sorry, something went wrong processing your request."


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()
    phone, message = whatsapp.parse_incoming_request(form)

    last_event_id = db.get_last_event_id(phone)
    last_event = db.get_event(last_event_id) if last_event_id else None

    now = datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None).isoformat(timespec="seconds")

    action = llm.interpret_message(message, now, last_event)
    reply_text = handle_action(phone, action)

    twiml = whatsapp.build_confirmation_twiml(reply_text)
    return Response(content=twiml, media_type="text/xml")


@app.get("/events")
async def get_events(phone: str):
    return db.get_events_for_phone(phone)


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
