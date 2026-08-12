import json
from typing import Literal, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

MODEL = "gemini-flash-lite-latest"

client = genai.Client()

SYSTEM_PROMPT = """You turn one WhatsApp message from a calendar app user into exactly one \
structured calendar action.

Rules:
- All dates/times are in the Asia/Jerusalem timezone. Always resolve relative dates \
("today", "tomorrow", "the day after tomorrow") against the "Current date and time" given to you.
- Output start_time/end_time as local ISO datetimes with no timezone suffix, e.g. "2026-08-14T16:00:00".
- action="create": the user is describing a brand new event. title, start_time, and end_time are \
all required. If the user gives a duration ("for one hour") but not an explicit end time, compute \
end_time from it. If neither a duration nor an end time is given, default to 1 hour.
- action="update": the user wants to change an existing event (time, title, etc). event_id must be \
the id of the "Last relevant event" provided to you — you have no other event list to search. Only \
include the fields that are changing; leave the rest null. If only start_time changes and no new \
duration/end_time is mentioned, shift end_time by the same amount as start_time so the original \
duration is preserved.
- action="cancel": the user wants to cancel/delete an existing event. event_id must be the id of the \
"Last relevant event" provided to you.
- action="clarify": use this whenever you cannot confidently produce create/update/cancel — e.g. the \
message isn't about a calendar at all, or it references an event that doesn't match the "Last relevant \
event" you were given (you have no way to search other events in this MVP). Put a short, friendly \
WhatsApp reply in reply_text explaining what you need or that you can't find that event.
- Never invent an event_id. If unsure which event is meant, use action="clarify" instead of guessing.
"""


class CalendarAction(BaseModel):
    action: Literal["create", "update", "cancel", "clarify"]
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_id: Optional[int] = None
    reply_text: Optional[str] = None


def interpret_message(message, now, last_event=None):
    user_content = (
        f"Current date and time: {now}\n"
        f"Last relevant event: {json.dumps(last_event) if last_event else 'None'}\n"
        f'User message: "{message}"'
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=CalendarAction,
            temperature=0,
        ),
    )

    result: CalendarAction = response.parsed

    return {
        "action": result.action,
        "title": result.title,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "event_id": result.event_id,
        "reply_text": result.reply_text,
    }
