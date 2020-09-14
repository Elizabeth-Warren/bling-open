from bling.transport import OutgoingMessage
from unittest.mock import MagicMock

import pytest

from bling.helpscout.mailboxes import Mailbox
from bling.outgoing import OutgoingHandler
from bling.phone import Phone
from bling.helpscout.client import NewCustomer, Thread, ThreadType


@pytest.fixture
def handler():
    hs_client = MagicMock()
    transport = MagicMock()

    return OutgoingHandler(hs_client, transport)


@pytest.fixture
def mailbox():
    return Mailbox(
        transport_type="twilio",
        phone=Phone.parse("+15556667777"),
        id=1,
        mc_campaign_id="",
    )


@pytest.fixture
def webhook_payload():
    return {
        "type": "phone",
        "id": 1,
        "customer": {"phone": "555-888-9999"},
        "threads": [
            # distractor
            {
                "type": "customer",
                "source": {"type": "web", "via": "user"},
                "createdAt": "2020-01-27T10:20:10Z",
                "body": "  msg A ",
            },
            # newest reply
            {
                "type": "agent",
                "source": {"type": "web", "via": "user"},
                "createdAt": "2020-01-27T10:20:30Z",
                "body": "  msg B ",
            },
            # distractor
            {
                "type": "agent",
                "source": {"type": "web", "via": "user"},
                "createdAt": "2020-01-27T10:20:20Z",
                "body": "  msg C ",
            },
        ],
    }


def test_send_reply(handler, mailbox, webhook_payload):
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    handler.transport.send_response.assert_called_with(
        OutgoingMessage(
            mailbox=mailbox, to_phone=Phone.parse("+15558889999"), body="msg B"
        )
    )

    handler.hs_client.add_thread_to_conversation.assert_called_with(
        1,
        Thread(
            customer=NewCustomer(email=Phone.parse("+15558889999").blackhole_email),
            type=ThreadType.PHONE,
            text=f"SMS reply sent successfully: msg B",
            imported=True,
        ),
    )


def test_non_phone_conversation(handler, mailbox, webhook_payload):
    webhook_payload["type"] = "email"
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_missing_conversation_id(handler, mailbox, webhook_payload):
    del webhook_payload["id"]
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_customer_phone_missing(handler, mailbox, webhook_payload):
    webhook_payload["customer"]["phone"] = None
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_non_agent_reply(handler, mailbox, webhook_payload):
    webhook_payload["threads"][1]["type"] = "customer"
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_non_web_source_type(handler, mailbox, webhook_payload):
    webhook_payload["threads"][1]["source"]["type"] = "email"
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_non_user_source_via(handler, mailbox, webhook_payload):
    webhook_payload["threads"][1]["source"]["via"] = "api"
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_empty_message(handler, mailbox, webhook_payload):
    webhook_payload["threads"][1]["body"] = "  \n  "
    handler.handle_outgoing_reply(mailbox, webhook_payload)

    assert handler.transport.send_response.call_count == 0
    assert handler.hs_client.add_thread_to_conversation.call_count == 0


def test_clean_text_html(handler):
    assert handler._clean_text(" abc <p>foo <br /> bar</p>  ") == "abc foo  bar"


def test_clean_text_signature(handler):
    assert (
        handler._clean_text("foo\nbar -- baz\n-- bax\n--\nsome signature")
        == "foo\nbar -- baz\n-- bax"
    )
