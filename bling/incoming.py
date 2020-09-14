from typing import Optional, Tuple

from bling.transport import Transport, OutgoingMessage, IncomingMesage
from bling.helpscout.client import (
    Conversation,
    HelpScoutClient,
    NewCustomer,
    Thread,
    ThreadType,
)

FIRST_MESSAGE_RESPONSE = "Team Warren has received your message, and you'll hear from us ASAP. Keep persisting!"

# The hard limit from Helpscout is 100, but we want a bit of headroom
MAX_CONVERSATION_LENGTH = 90


class IncomingHandler:
    """
    Handles a message from a supporter to the hotline number (either a text message or a voicemail)
    """

    def __init__(self, hs_client: HelpScoutClient, transport: Transport):
        self.hs_client = hs_client
        self.transport = transport

    def handle_message(self, message: IncomingMesage):
        customer = NewCustomer(
            email=message.from_phone.blackhole_email,
            phone=message.from_phone.helpscout_format,
            firstName=message.from_phone.helpscout_format,
        )

        thread = Thread(
            customer=customer,
            type=ThreadType.CUSTOMER,
            text=message.body,
            imported=False,
        )

        conversation_id, is_new_user = self._find_conversation_for_message(message)

        if conversation_id:
            # Add a thread to the existing conversation
            self.hs_client.add_thread_to_conversation(conversation_id, thread)
        else:
            # Create a new conversation
            self.hs_client.create_conversation(
                Conversation(
                    subject=f"Request from {message.from_phone.helpscout_format}",
                    customer=customer,
                    mailboxId=message.mailbox.id,
                    threads=[thread],
                )
            )

        if is_new_user:
            self.transport.send_response(
                OutgoingMessage(
                    to_phone=message.from_phone,
                    mailbox=message.mailbox,
                    body=FIRST_MESSAGE_RESPONSE,
                )
            )

    def _find_conversation_for_message(
        self, message: IncomingMesage
    ) -> Tuple[Optional[int], bool]:
        # Find which conversation to add the message to. In this
        # logic, we want to:
        #
        # - Try to keep messages from the same person in the same
        #   conversation as much as possible
        #
        # - Not put more than 90 messages in the same conversation.
        #   there's a hard limit of 100, and we want some head room
        #   for races, replies, etc.
        #
        # - Handle the case where two separate lambdas create two
        #   different conversations for the same user as cleanly as
        #   possible without introducing the complexity of locking or
        #   queueing (we might come back to this and add a lock or
        #   a queue if it becomes an issue, but we're trying this
        #   simpler approach first.)
        #
        # To achieve this:
        #
        # - If there is an existing conversation with the user that has
        #   less than 90 messages, use that one
        #
        # - Otherwise, create a new conversation
        #
        # Returns (conversation_id | None, is_new_user)
        conversations = self.hs_client.find_conversations(
            mailbox_ids=[message.mailbox.id],
            filters={"email": f'"{message.from_phone.blackhole_email}"'},
        )

        if len(conversations) == 0:
            return (None, True)

        conversation = conversations[0]
        return (
            conversation["id"]
            if conversation["threads"] < MAX_CONVERSATION_LENGTH
            else None,
            False,
        )
