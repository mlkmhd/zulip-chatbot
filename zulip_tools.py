import requests
from config import *


def get_last_message_id():
    try:
        with open('data/'+LAST_MSG_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_message_id(msg_id):
    os.makedirs("data", exist_ok=True)
    with open("data/"+LAST_MSG_ID_FILE, 'w') as f:
        f.write(str(msg_id))

def get_new_messages(anchor):
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
    requests.post(
        f"{ZULIP_BASE_URL}/api/v1/messages",
        data=payload,
        auth=(ZULIP_EMAIL, ZULIP_API_KEY)
    )