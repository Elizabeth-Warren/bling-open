from bling.api import format_twilio_sms


def test_format_twilio_sms():
    assert format_twilio_sms({}) == "(empty message)"
    assert format_twilio_sms({"Body": ""}) == "(empty message)"
    assert (
        format_twilio_sms(
            {
                "Body": "",
                "NumMedia": "1",
                "MediaContentType0": "text/plain",
                "MediaUrl0": "http://example.com",
            }
        )
        == "(empty message)\nAttachment (text/plain): http://example.com"
    )

    assert format_twilio_sms({"Body": "test"}) == "test"
    assert format_twilio_sms({"Body": "foo", "NumMedia": 0}) == "foo"
    assert (
        format_twilio_sms(
            {
                "Body": "foo",
                "NumMedia": 3,
                "MediaContentType0": "text/plain",
                "MediaUrl0": "http://example.com/0",
                "MediaUrl1": "http://example.com/1",
            }
        )
        == "foo\nAttachment (text/plain): http://example.com/0\nAttachment (unknown type): http://example.com/1\nAttachment (unknown type): (missing URL)"
    )
