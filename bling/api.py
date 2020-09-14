import logging
from typing import Any, Dict

from flask import Blueprint, request

from bling.helpscout.mailboxes import MAILBOXES_BY_ID, MAILBOXES_BY_TWILIO_PHONE

from bling.clients import (
    twilio_transport,
    incoming_message_handler,
    outgoing_reply_handler,
    transport_for_type,
)

from bling.transport import IncomingMesage
from bling.phone import Phone
from bling.common.utils import nested_get
from bling.helpscout.webhook import verify_help_scout_signature

from bling.twi.webhook import validate_twilio_request

mod = Blueprint("bling", __name__)


def twilio_empty_response():
    return "<Response></Response>", 200


def helpscout_empty_response():
    return "", 204


def format_twilio_sms(payload: Dict[str, Any]) -> str:
    body = payload.get("Body") or "(empty message)"

    for i in range(int(payload.get("NumMedia", "0"))):
        content_type = payload.get(f"MediaContentType{i}", "unknown type")
        url = payload.get(f"MediaUrl{i}", "(missing URL)")

        body += f"\nAttachment ({content_type}): {url}"

    return body


@mod.route("/", methods=["GET"])
def hello():
    return "Hello from Bling!", 200


@mod.route("/twilio_sms", methods=["POST"])
@validate_twilio_request
def twilio_sms():
    """
    Target for incoming SMSes from Twilio
    """
    data = request.form

    to_phone_twilio = data["To"]
    if to_phone_twilio not in MAILBOXES_BY_TWILIO_PHONE:
        # This will happen if you create a new phone number in Twilio and point
        # it to Bling, but don't configure Bling to handle that phone number.
        logging.warning(f"Bling got an SMS to an unknown phone: {to_phone_twilio}")
        return twilio_empty_response()

    mailbox = MAILBOXES_BY_TWILIO_PHONE[to_phone_twilio]
    from_phone = Phone.parse(data["From"])
    handler = incoming_message_handler(twilio_transport())

    handler.handle_message(
        IncomingMesage(
            mailbox=mailbox, from_phone=from_phone, body=format_twilio_sms(data)
        )
    )
    return twilio_empty_response()


@mod.route("/twilio_voicemail", methods=["POST"])
@validate_twilio_request
def twilio_voicemail():
    """
    Target for incoming voicemail from Twilio
    """

    data = request.form

    to_phone_twilio = data["to"]
    if to_phone_twilio not in MAILBOXES_BY_TWILIO_PHONE:
        logging.warning(f"Bling got a voicemail to an unknown phone: {to_phone_twilio}")
        return twilio_empty_response()

    mailbox = MAILBOXES_BY_TWILIO_PHONE[to_phone_twilio]
    from_phone = Phone.parse(data["from"])

    length = int(data.get("length") or 0)

    body = f"Caller left a voicemail ({length} seconds): {data['recording']}\n"

    incoming_message_handler(twilio_transport()).handle_message(
        IncomingMesage(mailbox=mailbox, from_phone=from_phone, body=body)
    )
    return twilio_empty_response()


@mod.route("/twilio_transcription", methods=["POST"])
@validate_twilio_request
def twilio_transcription():
    """
    Target for incoming transcriptions from Twilio
    """

    data = request.form

    to_phone_twilio = data["To"]
    if to_phone_twilio not in MAILBOXES_BY_TWILIO_PHONE:
        logging.warning(
            f"Bling got a transcription to an unknown phone: {to_phone_twilio}"
        )
        return twilio_empty_response()

    mailbox = MAILBOXES_BY_TWILIO_PHONE[to_phone_twilio]
    from_phone = Phone.parse(data["From"])

    status = data["TranscriptionStatus"]
    if status == "failed":
        body = f"Voicemail transcription failed, please listen to the recording: {data['RecordingUrl']}"
    else:
        body = f"Voicemail transcription: {data['TranscriptionText']}\n\nRecording: {data['RecordingUrl']}"

    incoming_message_handler(twilio_transport()).handle_message(
        IncomingMesage(mailbox=mailbox, from_phone=from_phone, body=body)
    )
    return twilio_empty_response()


@mod.route("/helpscout_webhook", methods=["POST"])
@verify_help_scout_signature
def helpscout_webhook():
    """
    Method called by Help Scout webhooks
    See: https://developer.helpscout.com/webhooks/
    """
    data = request.get_json()
    event_type = request.headers.get("X-HelpScout-Event")
    if not event_type:
        return "Bad request: missing event header", 400

    event_type = event_type.strip()
    mailbox_id = nested_get(data, "mailbox", "id")

    logging.info(
        "Received webhook with event_type %s, mailbox: %s", event_type, mailbox_id
    )

    mailbox = MAILBOXES_BY_ID.get(mailbox_id)
    if mailbox:
        outgoing_reply_handler(
            transport_for_type(mailbox.transport_type)
        ).handle_outgoing_reply(mailbox, data)

    return "", 204
