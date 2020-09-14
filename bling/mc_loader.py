import logging
from typing import Optional

from bling.transport import IncomingMesage, MobileCommonsTransport
from bling.helpscout.mailboxes import MAILBOXES_BY_CAMPAIGN_ID
from bling.clients import incoming_message_handler, mobilecommons_transport
from bling.phone import Phone


# This is a completely speculative implementation of a process for loading replies
# from mobilecommons. We expect that it's mostly sane: fetch messages from mobilecommons,
# find the mailbox appropriate for each message, and hand the IncomingMessage to
# our IncomingHandler. Users should use this program to poll the mobilecommons
# api with some realish time frequency (once every 5 minutes perhaps) and keep
# track of appropriate values for the start_str and end_str so that they do not
# wind up ingesting the same message twice. On AWS, a single valued dynamo table
# could be used to keep track of those values. Users could also use some value
# in that table to  implemented a distributed lock if appropriate. A very aggresive
# implementation would keep track of every message id that we ingest and check
# that table on subsequent runs to make sure we aren't ingesting the same message
# twice.
#
# It is worth remembering that the IncomingHandler does have a side effect: It
# texts the user that we've received the message and will get back to them shortly.
# that may or may not be appropriate for batch loads from mobilecommons.
def load_mobilecommons_incoming(
    start_str: str, end_str: str, transport: Optional[MobileCommonsTransport] = None
):
    if transport is None:
        transport = mobilecommons_transport()

    handler = incoming_message_handler(transport)
    count = 0

    for msg in transport.get_client().get_all_received_messages(start_str, end_str):
        campaign_id = msg.get("campaign_id")
        mailbox = MAILBOXES_BY_CAMPAIGN_ID.get(campaign_id)

        if mailbox is None:
            logging.warning(f"Failed to find a mailbox for message: '{msg}'")
            continue  # Early Continuation

        # Pulling these particular fields from the mobilecommons messages is
        # completely speculative. I have not been able to find mobilecommons
        # API documentation anywhere. But these are the sorts of fields that we do
        # find in send_sms responses so they seem reasonable. I'm similarly guessing
        # that we do not need to do much input validation on the phone_numbers
        # that we get back from mobilecommons because they've necesarily received
        # a text back from the number if it's part of this response. That may
        # or may not be a reasonable assumption
        handler.handle_message(
            IncomingMesage(
                mailbox=mailbox,
                from_phone=Phone.parse(msg.get("phone_number")),
                body=msg.get("body"),
            )
        )

        count += 1
        if count % 100:
            logging.info(f"Loaded {count} messages from mobilecommons")

    logging.info(f"Finished loading mobilecommons messages. Final count: {count}")
