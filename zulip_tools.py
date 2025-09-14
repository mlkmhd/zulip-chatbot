import requests
from config import *


def get_latest_message():
    url = f"{ZULIP_BASE_URL}/api/v1/messages"
    params = {
        "anchor": "newest",
        "num_before": 1,
        "num_after": 0,
        "narrow": f'[["stream", "{STREAM_NAME}"]]'
    }
    response = requests.get(url, params=params, auth=(ZULIP_EMAIL, ZULIP_API_KEY))
    response.raise_for_status()
    messages = response.json().get("messages", [])
    return messages[0] if messages else None

def get_new_messages_after(anchor):
    url = f"{ZULIP_BASE_URL}/api/v1/messages"
    params = {
        "anchor": anchor,
        "num_before": 0,
        "num_after": 10,
        "narrow": f'[["stream", "{STREAM_NAME}"]]'
    }
    response = requests.get(url, params=params, auth=(ZULIP_EMAIL, ZULIP_API_KEY))
    response.raise_for_status()
    return response.json().get("messages", [])

def send_message(stream, topic, content):
    payload = {
        "type": "stream",
        "to": stream,
        "topic": topic,
        "content": content,
    }

    # Send the message via Zulip REST API
    response = requests.post(
        f"{ZULIP_BASE_URL}/api/v1/messages",
        data=payload,
        auth=(ZULIP_EMAIL, ZULIP_API_KEY)
    )
    return response.json()

def update_message(message_id, new_content=None, new_topic=None):
    """
    Update a Zulip message's content and/or topic.
    """
    payload = {}
    if new_content is not None:
        payload["content"] = new_content
    if new_topic is not None:
        payload["topic"] = new_topic

    response = requests.patch(
        f"{ZULIP_BASE_URL}/api/v1/messages/{message_id}",
        data=payload,
        auth=(ZULIP_EMAIL, ZULIP_API_KEY)
    )
    return response.json()