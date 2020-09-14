from unittest.mock import MagicMock

import pytest

from bling.incoming import FIRST_MESSAGE_RESPONSE, IncomingHandler
from bling.transport import IncomingMesage, OutgoingMessage
from bling.helpscout.mailboxes import Mailbox
from bling.phone import Phone
from bling.helpscout.client import Conversation, NewCustomer, Thread, ThreadType


@pytest.fixture
def handler():
    hs_client = MagicMock()
    transport = MagicMock()

    return IncomingHandler(hs_client, transport)


@pytest.fixture
def mailbox():
    return Mailbox(
        transport_type="twilio",
        phone=Phone.parse("+15556667777"),
        id=1,
        mc_campaign_id="",
    )


def test_no_existing_conversation(handler, mailbox):
    handler.hs_client.find_conversations.return_value = []
    handler.handle_message(
        IncomingMesage(
            mailbox=mailbox,
            from_phone=Phone.parse("+15558889999"),
            body="Some text",
        )
    )

    # should create a new conversation and send a welcome text
    handler.hs_client.create_conversation.assert_called_with(
        Conversation(
            subject=f"Request from 555-888-9999",
            customer=NewCustomer(
                email="5558889999@helpscout-blackhole-local.elizabethwarren.com",
                phone="555-888-9999",
                firstName="555-888-9999",
            ),
            mailboxId=mailbox.id,
            threads=[
                Thread(
                    customer=NewCustomer(
                        email="5558889999@helpscout-blackhole-local.elizabethwarren.com",
                        phone="555-888-9999",
                        firstName="555-888-9999",
                    ),
                    type=ThreadType.CUSTOMER,
                    text="Some text",
                    imported=False,
                )
            ],
        )
    )

    assert handler.hs_client.add_thread_to_conversation.call_count == 0

    handler.transport.send_response.assert_called_with(
        OutgoingMessage(
            mailbox=mailbox,
            to_phone=Phone.parse("+15558889999"),
            body=FIRST_MESSAGE_RESPONSE,
        )
    )


def test_existing_conversation(handler, mailbox):
    handler.hs_client.find_conversations.return_value = [
        {"id": 456, "threads": 50},
        {"id": 123, "threads": 90},
    ]
    handler.handle_message(
        IncomingMesage(
            mailbox=mailbox, from_phone=Phone.parse("+15558889999"), body="Some text"
        )
    )

    # Should add to a existing conversation and not send a welcome text
    handler.hs_client.add_thread_to_conversation.assert_called_with(
        456,
        Thread(
            customer=NewCustomer(
                email="5558889999@helpscout-blackhole-local.elizabethwarren.com",
                phone="555-888-9999",
                firstName="555-888-9999",
            ),
            type=ThreadType.CUSTOMER,
            text="Some text",
            imported=False,
        ),
    )

    assert handler.hs_client.create_conversation.call_count == 0
    assert handler.transport.send_response.call_count == 0


def test_existing_long_conversation(handler, mailbox):
    handler.hs_client.find_conversations.return_value = [
        {"id": 456, "threads": 90},
        {"id": 123, "threads": 50},
    ]
    handler.handle_message(
        IncomingMesage(
            mailbox=mailbox, from_phone=Phone.parse("+15558889999"), body="Some text"
        )
    )

    # Should create a new conversation but not send a welcome text
    handler.hs_client.create_conversation.assert_called_with(
        Conversation(
            subject=f"Request from 555-888-9999",
            customer=NewCustomer(
                email="5558889999@helpscout-blackhole-local.elizabethwarren.com",
                phone="555-888-9999",
                firstName="555-888-9999",
            ),
            mailboxId=mailbox.id,
            threads=[
                Thread(
                    customer=NewCustomer(
                        email="5558889999@helpscout-blackhole-local.elizabethwarren.com",
                        phone="555-888-9999",
                        firstName="555-888-9999",
                    ),
                    type=ThreadType.CUSTOMER,
                    text="Some text",
                    imported=False,
                )
            ],
        )
    )

    assert handler.hs_client.add_thread_to_conversation.call_count == 0
    assert handler.transport.send_response.call_count == 0
