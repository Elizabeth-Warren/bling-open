# From: https://www.twilio.com/docs/usage/tutorials/how-to-secure-your-flask-app-by-validating-incoming-twilio-requests

import logging
from functools import wraps

from flask import abort, request

from bling.common.request_url import request_url
from bling.config import config
from twilio.request_validator import RequestValidator


def validate_twilio_request(f):
    """Validates that incoming requests genuinely originated from Twilio"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Create an instance of the RequestValidator class
        validator = RequestValidator(config.twilio_auth_token)

        url = request_url()

        # Validate the request using its URL, POST data,
        # and X-TWILIO-SIGNATURE header
        request_valid = validator.validate(
            url, request.form, request.headers.get("X-TWILIO-SIGNATURE", "")
        )

        # Continue processing the request if it's valid, return a 403 error if
        # it's not
        if request_valid:
            return f(*args, **kwargs)
        else:
            logging.warning(
                f"Invalid Twilio signature :: {url} :: {request.headers.get('X-TWILIO-SIGNATURE', '')} :: {request.form}"
            )
            return abort(403)

    return decorated_function
