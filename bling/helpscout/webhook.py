import base64
import functools
import hashlib
import hmac

from flask import request

from bling.config import config


def verify_help_scout_signature(f):
    """Middleware to validate Help Scout API calls
    https://developer.helpscout.com/webhooks/#verifying
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        sig = request.headers.get("X-HelpScout-Signature")
        if not _is_valid_signature(
            config.helpscout_webhook_secret, request.get_data(as_text=False), sig
        ):
            return "Unauthorized: Failed Help Scout signature verification", 401
        else:
            return f(*args, **kwargs)

    return wrapped


def _is_valid_signature(secret, data_bytes, signature_string):
    if not signature_string:
        return False
    digest = hmac.digest(
        bytes(secret, "UTF-8"), msg=data_bytes, digest=hashlib.sha1  # type: ignore
    )
    return hmac.compare_digest(digest, base64.b64decode(signature_string))
