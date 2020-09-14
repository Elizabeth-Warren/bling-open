import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional

import requests
import xmltodict
from dateutil import parser as date_parser

from bling.common.utils import nested_get

MOBILE_COMMONS_API_BASE = "https://secure.mcommons.com/api/"
MOBILE_COMMONS_SIGNUP_URL = "https://secure.mcommons.com/profiles/join"


@dataclass
class Message:
    id: int
    message_type: str
    status: str
    body: str
    when: Optional[datetime]
    campaign_id: Optional[int]

    @staticmethod
    def from_xml_dict(d):
        created_at = d.get("when", "")
        campaign_id = nested_get(d, "campaign", "id")
        return Message(
            id=int(d["id"]),
            message_type=d.get("message_type"),
            status=d.get("status"),
            body=d.get("body"),
            when=date_parser.parse(created_at) if created_at else None,
            campaign_id=int(campaign_id) if campaign_id else None,
        )


@dataclass
class Profile:
    id: int
    phone_number: str
    first_name: str
    last_name: str
    opted_out_at: Optional[datetime]
    campaign_ids: Set[int]
    custom_fields: Dict[str, str]
    messages: List[Message]
    messages_are_sorted: bool = field(default=False)

    def sort_messages_desc(self):
        if not self.messages_are_sorted:
            self.messages.sort(key=lambda m: m.when, reverse=True)  # type: ignore
            self.messages_are_sorted = True

    def most_recent_message(self):
        self.sort_messages_desc()
        return self.messages[0]

    @staticmethod
    def from_xml_dict(d):
        subscriptions = _extract_mc_repeated_field(d, "subscriptions", "subscription")
        campaign_ids = set(int(s["campaign_id"]) for s in subscriptions)
        custom_fields = {
            c["name"]: c.get("value")
            for c in _extract_mc_repeated_field(d, "custom_columns", "custom_column")
        }
        messages = [
            Message.from_xml_dict(m)
            for m in _extract_mc_repeated_field(d, "messages", "message")
        ]
        opt_out_time = d.get("opted_out_at", "")
        return Profile(
            id=int(d["id"]),
            phone_number=d["phone_number"],
            first_name=d.get("first_name"),
            last_name=d.get("last_name"),
            opted_out_at=date_parser.parse(opt_out_time) if opt_out_time else None,
            campaign_ids=campaign_ids,
            custom_fields=custom_fields,
            messages=messages,
        )


def _extract_mc_repeated_field(data, plural, singular):
    """Helper to extract repeated fields from xml consistently.

    Without this single element lists get returned as dicts
    """
    f = data.get(plural, {}).get(singular, [])
    if type(f) == list:
        return f
    else:
        return [f]


class MobileCommonsAPIException(Exception):
    pass


class MobileCommonsClient:
    def __init__(self, username, password, session=None):
        self.username = username
        self.password = password
        self.session = session if not None else requests.Session()

    def post_to_mobile_commons(self, api_method, payload):
        try:
            url = MOBILE_COMMONS_API_BASE + api_method
            resp = self.session.post(
                url, auth=(self.username, self.password), json=payload
            )
            # logging.info(f"Response from MC {api_method}: {resp.text[0:400]}")
            return resp
        except RuntimeError:
            logging.exception("Error posting to MC")

    # TODO: allow passing a message type
    def send_sms(self, campaign_id, phone_number, message):
        payload = {
            "campaign_id": campaign_id,
            "phone_number": phone_number,
            "body": message,
        }
        return self.post_to_mobile_commons("send_message", payload)

    def opt_out(self, phone_number, campaign_id=None, session=None):
        payload = {"phone_number": phone_number}
        if campaign_id:
            payload["campaign_id"] = campaign_id
        self.post_to_mobile_commons("profile_opt_out", payload)

    def get_profile(self, phone_number, include_messages=False):
        payload = {
            "phone_number": phone_number,
            "include_messages": 1 if include_messages else 0,
        }
        response = self.post_to_mobile_commons("profile", payload)
        data = xmltodict.parse(response.text, attr_prefix="", cdata_key="value")
        if nested_get(data, "response", "success") == "true":
            return nested_get(data, "response", "profile")
        else:
            return None

    # TODO: use get_profile
    def profile_exists(self, phone_number):
        payload = {"phone_number": phone_number}
        response = self.post_to_mobile_commons("profile", payload)
        try:
            d = xmltodict.parse(response.text, attr_prefix="", cdata_key="value")
            return (
                "response" in d
                and "success" in d["response"]
                and d["response"]["success"] == "true"
            )
        except (RuntimeError, KeyError, xmltodict.expat.ExpatError):
            logging.exception(f"Failed to read mobile commons response {response.text}")

    def create_or_update_mobile_commons_profile(self, payload):
        return self.post_to_mobile_commons("profile_update", payload)

    def create_or_update_mobile_commons_profile_via_web(
        self, web_opt_in_path_key, profile_payload
    ):
        """Similar to above, but for a web opt-in path.

        This mechanism allows resubscription of people who have previously
        opted out -- so be careful.
        """
        form_data = {
            "opt_in_path[]": web_opt_in_path_key,
            "person[phone]": profile_payload["phone_number"],
        }
        for k, v in profile_payload.items():
            form_data[f"person[{k}]"] = v
        return requests.post(MOBILE_COMMONS_SIGNUP_URL, data=form_data)

    def get_all_received_messages(
        self,
        start_str,
        end_str,
        start_page=1,
        end_page=None,
        limit_per_page=100,
        retry_wait=50,
        retry_limit=3,
    ):

        page = start_page
        all_data = []
        params = {"limit": limit_per_page, "start_time": start_str, "end_time": end_str}
        url = MOBILE_COMMONS_API_BASE + "messages"
        fails = 0

        while True:
            if end_page and page >= end_page:
                break
            time.sleep(fails * retry_wait)

            params["page"] = page
            logging.debug(f"Requesting {url} with params {params}")

            try:
                resp = self.session.get(
                    url, params=params, auth=(self.username, self.password)
                )

                data = xmltodict.parse(resp.text, attr_prefix="", cdata_key="value")

                error_code = nested_get(data, "response", "error", "id")
                if error_code:
                    raise MobileCommonsAPIException(
                        f"Error with Mobile Commons API. Error code {error_code}. Response: {resp.text}"
                    )

                data = nested_get(data, "response", "messages", "message", default=[])
                if type(data) == OrderedDict:
                    data = [
                        data
                    ]  # if the page has exactly one item it gets parsed as a dict instead of a list
                all_data.extend(data)

                if len(data) < limit_per_page:
                    break

                if resp.status_code in [429]:
                    logging.warning("429: Rate limit - waiting 2 seconds")
                    time.sleep(2)
                    continue

                resp.raise_for_status()

            except (
                requests.exceptions.RequestException,
                MobileCommonsAPIException,
            ):
                fails += 1
                logging.exception("Mobile commons exception")
                if fails > retry_limit:
                    raise

            page += 1

        return all_data
