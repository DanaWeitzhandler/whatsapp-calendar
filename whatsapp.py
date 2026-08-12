from twilio.twiml.messaging_response import MessagingResponse

WHATSAPP_PREFIX = "whatsapp:"


def parse_incoming_request(form):
    phone = form.get("From", "")
    if phone.startswith(WHATSAPP_PREFIX):
        phone = phone[len(WHATSAPP_PREFIX):]
    message = form.get("Body", "")
    return phone, message


def build_confirmation_twiml(text):
    response = MessagingResponse()
    response.message(text)
    return str(response)
