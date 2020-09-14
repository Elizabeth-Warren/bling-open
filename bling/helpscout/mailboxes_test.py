from bling.helpscout.mailboxes import Mailbox, parse_mailboxes
from bling.phone import Phone


def test_parse_mailboxes():
    assert parse_mailboxes("") == []

    print(parse_mailboxes("twilio:+15556667777:123"))
    print(
        [
            Mailbox(
                transport_type="twilio",
                phone=Phone.parse("+15556667777"),
                id=123,
                mc_campaign_id="",
            )
        ]
    )

    assert parse_mailboxes("twilio:+15556667777:123") == [
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15556667777"),
            id=123,
            mc_campaign_id="",
        )
    ]

    assert parse_mailboxes("    twilio :  +15556667777  :  123  ") == [
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15556667777"),
            id=123,
            mc_campaign_id="",
        )
    ]

    assert parse_mailboxes("twilio:+15556667777:123,twilio:+15558889999:456") == [
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15556667777"),
            id=123,
            mc_campaign_id="",
        ),
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15558889999"),
            id=456,
            mc_campaign_id="",
        ),
    ]

    assert parse_mailboxes(
        " twilio:  (555) 666-7777 : 123  , twilio: + 1 5558889999: 456"
    ) == [
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15556667777"),
            id=123,
            mc_campaign_id="",
        ),
        Mailbox(
            transport_type="twilio",
            phone=Phone.parse("+15558889999"),
            id=456,
            mc_campaign_id="",
        ),
    ]

    assert parse_mailboxes("mobilecommons: test-campaign: 123") == [
        Mailbox(
            transport_type="mobilecommons",
            phone=Phone.parse("5555555555"),
            id=123,
            mc_campaign_id="test-campaign",
        )
    ]
