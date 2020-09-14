from werkzeug.utils import cached_property
from os import environ


class Config:
    @cached_property
    def helpscout_api_client_id(self):
        return environ.get("HELPSCOUT_API_CLIENT_ID")

    @cached_property
    def helpscout_api_client_secret(self):
        return environ.get("HELPSCOUT_API_CLIENT_SECRET")

    @cached_property
    def helpscout_webhook_secret(self):
        return environ.get("HELPSCOUT_WEBHOOK_SECRET")

    @cached_property
    def twilio_account_sid(self):
        return environ.get("TWILIO_ACCOUNT_SID")

    @cached_property
    def twilio_auth_token(self):
        return environ.get("TWILIO_AUTH_TOKEN")

    @cached_property
    def mobilecommons_username(self):
        return environ.get("MOBILECOMMONS_USERNAME")

    @cached_property
    def mobilecommons_password(self):
        return environ.get("MOBILECOMMONS_PASSWORD")

    @cached_property
    def blackhole_domain(self):
        """We use a different domain for each set of infrastructure so they
        create separate Helpscout customers"""
        return environ.get(
            "BLACKHOLE_DOMAIN", "helpscout-blackhole-local.elizabethwarren.com"
        )


config = Config()
