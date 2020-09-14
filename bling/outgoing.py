import logging
from typing import Any, Dict

from dateutil import parser as date_parser
from lxml import html

from bling.helpscout.mailboxes import Mailbox
from bling.phone import Phone
from bling.common.utils import nested_get
from bling.helpscout.client import HelpScoutClient, NewCustomer, Thread, ThreadType
from bling.transport import Transport, OutgoingMessage


class OutgoingHandler:
    """
    Handles sending an outgoing reply in response to a Helpscout agent replying to the ticket
    """

    def __init__(self, hs_client: HelpScoutClient, transport: Transport):
        self.hs_client = hs_client
        self.transport = transport

    def handle_outgoing_reply(self, mailbox: Mailbox, webhook_payload: Dict[str, Any]):
        # Ignore email conversations
        if webhook_payload.get("type") != "phone":
            logging.info("Non-phone conversation")
            return

        # Get conversation id
        conversation_id = webhook_payload.get("id")
        if not conversation_id:
            logging.warning(f"Payload missing ID: {webhook_payload}")
            return

        # Get user phone
        user_helpscout_phone = nested_get(webhook_payload, "customer", "phone")
        if not user_helpscout_phone:
            logging.warning(f"Payload user phone: {webhook_payload}")
            return

        user_phone = Phone.parse(user_helpscout_phone)  # type: ignore

        # Get the actual reply
        threads = sorted(
            webhook_payload["threads"],
            key=lambda t: date_parser.parse(t["createdAt"]),
            reverse=True,
        )
        most_recent = threads[0]

        # Check that this reply was created by an agent through the web interface
        source_type = nested_get(most_recent, "source", "type")
        source_via = nested_get(most_recent, "source", "via")
        if (
            most_recent["type"] == "customer"
            or source_type != "web"
            or source_via != "user"
        ):
            logging.error(
                f"Most recent thread does not appear to have been created by an agent: {most_recent}"
            )
            return

        body = self._clean_text(most_recent.get("body", ""))
        if body == "":
            logging.error(f"Empty message text: {most_recent.get('body')}")
            return

        # Send the text
        self.transport.send_response(
            OutgoingMessage(mailbox=mailbox, to_phone=user_phone, body=body)
        )

        # Confirm that it was sent by adding a note to the conversation
        self.hs_client.add_thread_to_conversation(
            conversation_id,
            Thread(
                customer=NewCustomer(email=user_phone.blackhole_email),
                type=ThreadType.PHONE,
                text=f"SMS reply sent successfully: {body}",
                imported=True,
            ),
        )

    def _clean_text(self, text: str) -> str:
        if "<" in text:
            plaintext = html.document_fromstring(text).text_content().strip()
        else:
            plaintext = text.strip()

        return plaintext.rsplit("\n--\n", 1)[0].strip()
