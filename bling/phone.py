from dataclasses import dataclass

import phonenumbers

from bling.config import config


# For each phone number, we contruct a "blackhole" email
# address because all conversations in Help Scout must
# have a contact email. Deriving the email from the phone
# number rather than making it random makes it easy to thread
# messages from the same person together in Help Scout.
def blackhole_email(national_phone_number: str) -> str:
    return f"{national_phone_number}@{config.blackhole_domain}"


@dataclass
class Phone:
    """
    A phone number. Provides the number formatted for Twilio, Helpscout, or a
    a "black-hole" address we can use as a Helpscout contact email.
    """

    twilio_format: str
    helpscout_format: str
    blackhole_email: str

    @staticmethod
    def parse(input_phone: str):
        phone = phonenumbers.parse(input_phone, "US")
        national_phone = str(phone.national_number)

        helpscout_format = (
            f"{national_phone[:3]}-{national_phone[3:6]}-{national_phone[6:]}"
        )

        twilio_format = f"+{phone.country_code}{national_phone}"

        return Phone(
            twilio_format=twilio_format,
            helpscout_format=helpscout_format,
            blackhole_email=blackhole_email(national_phone),
        )
