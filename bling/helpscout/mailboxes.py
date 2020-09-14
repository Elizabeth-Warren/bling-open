import os
from dataclasses import dataclass

from bling.phone import Phone


@dataclass
class Mailbox:
    """
    A Helpscout mailbox that's using Bling.
    """

    transport_type: str
    phone: Phone
    id: int
    mc_campaign_id: str


# Parse mailbox config: comma-separated mailboxes in the format <twilio number>:<mailbox id>
def parse_mailboxes(configs_str):
    if (len(configs_str.strip())) == 0:
        return []

    mailbox_configs = [
        config.split(":") for config in configs_str.split(",") if config.strip()
    ]

    mailboxes = []
    for transport_type, transport_value, mailbox_id in mailbox_configs:
        transport_type = transport_type.strip()
        mailbox_id = mailbox_id.strip()
        transport_value = transport_value.strip()

        if transport_type == "twilio":
            mailboxes.append(
                Mailbox(
                    transport_type=transport_type,
                    id=int(mailbox_id),
                    phone=Phone.parse(transport_value),
                    mc_campaign_id="",
                )
            )
        elif transport_type == "mobilecommons":
            mailboxes.append(
                Mailbox(
                    transport_type=transport_type,
                    id=int(mailbox_id),
                    phone=Phone.parse("5555555555"),
                    mc_campaign_id=transport_value,
                )
            )
    return mailboxes


# Parse the mailbox config and index by Twilio phone number and mailbox ID
MAILBOXES = parse_mailboxes(
    os.environ.get("BLING_MAILBOXES", "twilio:+16173973198:206906")
)

MAILBOXES_BY_TWILIO_PHONE = {}
MAILBOXES_BY_CAMPAIGN_ID = {}
MAILBOXES_BY_ID = {}

for mb in MAILBOXES:
    MAILBOXES_BY_TWILIO_PHONE[mb.phone.twilio_format] = mb
    MAILBOXES_BY_CAMPAIGN_ID[mb.mc_campaign_id] = mb
    MAILBOXES_BY_ID[mb.id] = mb
