import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Union

import requests

from bling.config import config
from bling.common.utils import nested_get

HELPSCOUT_BASE_URL = "https://api.helpscout.net"


class ThreadType(Enum):
    """Representation of the different message types (confusingly called threads in HS)
    that can appear in a conversation.

    Not a great api:
    type_name is the name as it appears in the "type" field in json serialized thread objects
    path_name is the name as it appears in the path of a POST request, sometimes this is the plural
      of type name, sometimes it's not :(
    """

    REPLY = ("reply", "reply")
    CUSTOMER = ("customer", "customer")
    CHAT = ("chat", "chats")
    PHONE = ("phone", "phones")
    EMAIL = ("email", "emails")
    NOTE = ("note", "notes")

    def __init__(self, type_name, path_name):
        self.type_name = type_name
        self.path_name = path_name

    def __str__(self):
        return self.type_name


@dataclass
class NewCustomer:
    id: Optional[int] = None
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class Thread:
    """Partial representation of a Help Scout Thread resource for the POST endpoint

    https://developer.helpscout.com/mailbox-api/endpoints/conversations/threads/reply/
    """

    type: ThreadType
    text: str
    imported: bool
    customer: Optional[Union[NewCustomer, Dict[str, Any]]] = None
    createdAt: Optional[str] = None


@dataclass
class Conversation:
    """Partial representation of a Help Scout Conversation resource for the POST endpoint

    https://developer.helpscout.com/mailbox-api/endpoints/conversations/create/
    """

    subject: str
    customer: NewCustomer
    mailboxId: int
    threads: List[Thread]
    tags: List[str] = field(default_factory=list)
    status: str = field(default="active")
    type: str = field(default="phone")
    autoReply: bool = field(default=False)


class HelpScoutClient:
    def __init__(self, base_url=HELPSCOUT_BASE_URL, client_id=None, secret=None):
        self._session = requests.session()
        self._base_url = base_url.strip("/")
        self._client_id = client_id or config.helpscout_api_client_id
        self._secret = secret or config.helpscout_api_client_secret
        self._token = None
        self._authenticate()

    def _authenticate(self):
        res = self._session.request(
            method="POST",
            url=self._base_url + "/v2/oauth2/token",
            params={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._secret,
            },
        )
        res.raise_for_status()
        self._token = res.json()["access_token"]

    def _make_request(
        self, method, path, params=None, json_body=None, absolute_url=False
    ):
        logging.debug(f"[{method}] {path} params={params} json_body={json_body}")
        url = path if absolute_url else self._base_url + path

        def _req():
            return self._session.request(
                method=method,
                headers={"Authorization": f"Bearer {self._token}"},
                url=url,
                json=json_body,
                params=params,
            )

        res = _req()
        if res.status_code == 429:
            sleep_seconds = int(res.headers.get("X-RateLimit-Retry-After", 60))
            logging.info(
                f"Help Scout rate limit exceeded sleeping {sleep_seconds} seconds"
            )
            time.sleep(sleep_seconds)
            res = _req()
        if res.status_code == 401:
            self._authenticate()
            res = _req()
        try:
            res.raise_for_status()
        except requests.HTTPError as e:
            logging.error(f"Error response from Help Scout {e.response.content}")
            raise e
        return res

    def get_customer(self, customer_id):
        """https://developer.helpscout.com/mailbox-api/endpoints/customers/get/"""
        return self._make_request("GET", f"/v2/customers/{customer_id}")

    def create_customer(
        self, first_name, last_name, mobile_phone, email, background=None
    ):
        """https://developer.helpscout.com/mailbox-api/endpoints/customers/create/"""

        if first_name is None and last_name is None:
            # first and last name can't both be null, so set first to the phone number
            first_name = mobile_phone

        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "phones": [{"value": str(mobile_phone), "type": "mobile"}],
            "emails": [{"value": email, "type": "other"}],
        }
        if background:
            payload["background"] = background
        res = self._make_request("POST", "/v2/customers", json_body=payload)
        return res.headers["Resource-ID"]

    def create_conversation(self, conversation: Conversation):
        """https://developer.helpscout.com/mailbox-api/endpoints/conversations/create/"""
        payload = asdict(conversation)
        for t in payload["threads"]:
            # This would be cleaner if we could make the enum serializable
            t["type"] = str(t["type"])
            # createdAt not supported when imported = false
            if not t["imported"]:
                del t["createdAt"]
        return self._make_request("POST", "/v2/conversations", json_body=payload)

    def find_conversations(
        self,
        mailbox_ids: List[int] = None,
        status: str = "all",
        filters: Dict[str, Any] = {},
        sort_field: str = "createdAt",
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """https://developer.helpscout.com/mailbox-api/endpoints/conversations/list/"""
        params = {"status": status, "sortField": sort_field, "sortOrder": sort_order}

        if mailbox_ids:
            params["mailbox"] = ",".join(str(i) for i in mailbox_ids)

        if filters:
            query = " AND ".join([f"{k}:{v}" for k, v in filters.items()])
            params["query"] = f"({query})"

        return self._make_request("GET", "/v2/conversations", params=params).json()[
            "_embedded"
        ]["conversations"]

    def find_conversations_for_customer(
        self, customer_id: int, mailbox_ids: List[int] = None, status: str = "all"
    ):
        """https://developer.helpscout.com/mailbox-api/endpoints/conversations/list/"""
        return self.find_conversations(
            mailbox_ids=mailbox_ids, status=status, filters={"customerIds": customer_id}
        )

    def get_threads_for_conversation(self, conversation_id):
        # TODO: paginate by default?
        return self._make_request("GET", f"/v2/conversations/{conversation_id}/threads")

    def delete_thread(self, conversation_id, thread_id):
        return self._make_request(
            "PATCH",
            f"/v2/conversations/{conversation_id}/threads/{thread_id}",
            json_body={"op": "remove"},
        )

    def add_thread_to_conversation(self, conversation_id: int, thread: Thread):
        """https://developer.helpscout.com/mailbox-api/endpoints/conversations/threads/reply/"""
        payload = asdict(thread)
        del payload["type"]  # not needed here since we use the type in the path name
        # createdAt not supported when imported = false
        if not thread.imported:
            del payload["createdAt"]
        return self._make_request(
            "POST",
            f"/v2/conversations/{conversation_id}/{thread.type.path_name}",
            json_body=payload,
        )

    def move_conversation(self, conversation_id, new_mailbox):
        """https://developer.helpscout.com/mailbox-api/endpoints/conversations/update/"""
        payload = {"op": "move", "path": "/mailboxId", "value": new_mailbox}
        return self._make_request(
            "PATCH", f"/v2/conversations/{conversation_id}", json_body=payload
        )

    def get_conversation(self, conversation_id: int, include_threads=False):
        params = None
        if include_threads:
            params = {"embed": "threads"}
        return self._make_request(
            "GET", f"/v2/conversations/{conversation_id}", params=params
        )

    def list_conversations(self, mailbox_id: int) -> Iterator[requests.Response]:
        return self._paginate(
            self._make_request(
                "GET", f"/v2/conversations", params={"mailbox": mailbox_id}
            )
        )

    def _paginate(
        self, first_page_response: requests.Response
    ) -> Iterator[requests.Response]:
        """Generic method to paginate through any Help Scout GET result

        This yields the first page, so that it can be used to process all pages, eg.:
        gen = client._paginate(client.get_threads_for_conversation(123))
        for page in gen:
            ...
        """
        page = first_page_response
        while True:
            yield page
            next_page = nested_get(page.json(), "_links", "next", "href")
            if not next_page:
                break
            page = self._make_request("GET", next_page, absolute_url=True)

    def update_conversation_tags(
        self, conversation_id, remove: List[str] = None, add: List[str] = None
    ):
        """Remove and add tags to a conversation.

        Note: Tags are passed by name, not id
        """
        add = add if add else []
        remove = set(remove) if remove else set()  # type: ignore
        previous_tags = self.get_conversation(conversation_id).json()["tags"]
        tags = [t["tag"] for t in previous_tags if t["tag"] not in remove]
        for t in add:
            if t not in tags:
                tags.append(t)

        return self.put_conversation_tags(conversation_id, tags)

    def put_conversation_tags(self, conversation_id: int, tags: List[str]):
        """Set conversation tags, this overwrites existing tags.
        Note: Tags are passed by name, not id.

        https://developer.helpscout.com/mailbox-api/endpoints/conversations/tags/update/
        """
        payload = {"tags": tags}
        return self._make_request(
            "PUT", f"/v2/conversations/{conversation_id}/tags", json_body=payload
        )

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
