from bling.helpscout.client import HelpScoutClient
from bling.mc.client import MobileCommonsClient
from twilio.rest import Client as TwilioClient

from bling.incoming import IncomingHandler
from bling.outgoing import OutgoingHandler
from bling.config import config


from bling.transport import (
    Transport,
    TwilioTransport,
    MobileCommonsTransport,
    TWILIO_TRANSPORT_TYPE,
    MOBILECOMMONS_TRANSPORT_TYPE,
)


def helpscout_client() -> HelpScoutClient:
    return HelpScoutClient(
        client_id=config.helpscout_api_client_id,
        secret=config.helpscout_api_client_secret,
    )


def twilio_client() -> TwilioClient:
    return TwilioClient(config.twilio_account_sid, config.twilio_auth_token)


def twilio_transport() -> TwilioTransport:
    return TwilioTransport(twilio_client())


def mobilecommons_client() -> MobileCommonsClient:
    return MobileCommonsClient(
        config.mobilecommons_username, config.mobilecommons_password
    )


def mobilecommons_transport() -> MobileCommonsTransport:
    return MobileCommonsTransport(mobilecommons_client())


def incoming_message_handler(transport: Transport) -> IncomingHandler:
    return IncomingHandler(helpscout_client(), transport)


def transport_for_type(transport_type: str) -> Transport:
    if transport_type == TWILIO_TRANSPORT_TYPE:
        return twilio_transport()
    elif transport_type == MOBILECOMMONS_TRANSPORT_TYPE:
        return mobilecommons_transport()
    else:
        raise Exception(f"'{transport_type}' is not a valid transport type'")


def outgoing_reply_handler(transport: Transport) -> OutgoingHandler:
    return OutgoingHandler(helpscout_client(), transport)