from bling.phone import Phone


def test_parse():
    assert Phone.parse("+15556667777") == Phone(
        twilio_format="+15556667777",
        helpscout_format="555-666-7777",
        blackhole_email="5556667777@helpscout-blackhole-local.elizabethwarren.com",
    )

    assert Phone.parse("555-666-7777") == Phone(
        twilio_format="+15556667777",
        helpscout_format="555-666-7777",
        blackhole_email="5556667777@helpscout-blackhole-local.elizabethwarren.com",
    )
