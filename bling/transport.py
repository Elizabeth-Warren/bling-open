from dataclasses import dataclass
from typing import Union

from bling.helpscout.mailboxes import Mailbox
from bling.mc.client import MobileCommonsClient
from bling.phone import Phone
from twilio.rest import TwilioClient

TWILIO_TRANSPORT_TYPE = "twilio"
MOBILECOMMONS_TRANSPORT_TYPE = "mobilecommons"


@dataclass
class IncomingMesage:
    mailbox: Mailbox
    from_phone: Phone
    body: str


@dataclass
class OutgoingMessage:
    mailbox: Mailbox
    to_phone: Phone
    body: str


class Transport:
    def get_client(self) -> Union[MobileCommonsClient, TwilioClient]:
        raise NotImplementedError("'get_client' is not implemented on this transport")

    def send_response(self, message: OutgoingMessage):
        raise NotImplementedError(
            "'send_response' is not implemented on this transport"
        )


class TwilioTransport(Transport):
    def __init__(self, client: TwilioClient):
        self.client = client

    def get_client(self) -> TwilioClient:
        return self.client

    def send_response(self, message: OutgoingMessage):
        return self.client.messages.create(
            to=message.to_phone.twilio_format,
            from_=message.mailbox.phone.twilio_format,
            body=message.body,
        )


class MobileCommonsTransport(Transport):
    def __init__(self, client: MobileCommonsClient):
        self.client = client

    def get_client(self) -> MobileCommonsClient:
        return self.client

    def send_response(self, message: OutgoingMessage):
        return self.client.send_sms(
            message.mailbox.mc_campaign_id, message.to_phone.twilio_format, message.body
        )
