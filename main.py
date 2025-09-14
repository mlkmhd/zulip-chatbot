import html2text
import re
from zulip_tools import *
from gitlab_tools import *
from config import *


help_message = ("**Available commands:** \n\n**1- prints list of commands** \n/help"
                "\n/deploy\nenv: [dev, sandbox, prod] \nversion: 1.2.3")

def main():

    last_message = get_latest_message()
    last_message_id = last_message['id']

    while True:
        messages = get_new_messages_after(anchor=last_message_id+1)
        for msg in messages:
            content = html2text.html2text(msg["content"].lower())
            sender = msg["sender_full_name"]
            msg_id = msg["id"]
            topic_name = msg["subject"]
            print(f"Message: {content}")

            if content.startswith("/"):

                if content.startswith("/help"):
                    send_message(STREAM_NAME, topic_name, help_message)

                elif content.startswith("/deploy"):
                    message_result = send_message(STREAM_NAME, topic_name, ":clock: I got your order, please wait some seconds...")
                    message_id = message_result['id']
                    new_version = re.search(r"version:\s*(\d+\.\d+\.\d+)", content)
                    try:
                        update_project_version(GITLAB_MR_GENERATOR_PROJECT_PATH, new_version)
                        update_message(message_id, ":check: the project has been updated")
                    except ValueError as e:
                        print("Oops! That wasn’t a number:", e)
                        update_message(message_id, ":incorrect: failed to update the project")

                elif content.startswith("/env"):
                    message_result = send_message(STREAM_NAME, topic_name, f":clock: I got your order. please wait some seconds to collect ports...")
                    message_id = message_result['id']

                    project_name = topic_name.lower().replace(" release", "").strip()
                    envs = get_project_environments(project_name)

                    if not envs:
                        response = f"No deployment environments found for {project_name}"
                    else:
                        response = f"**{project_name} is deployed to:**\n"
                        for env in envs:
                            response += f"- {env[0]}\n"
                            response += f"    - url: {env[1]}\n"
                            response += f"    - version: {env[2]}\n"
                            response += f"    - nodeports: \n"
                            for port in env[3]:
                                response += f"        • {port['port-name']}: {port['port-number']}\n"
                    update_message(message_id, response)
                else:
                    send_message(STREAM_NAME, topic_name, "your command not found!")
                    send_message(STREAM_NAME, topic_name, help_message)

            last_message_id = msg_id

        time.sleep(3)  # wait 5 seconds and re-pull again

if __name__ == "__main__":
    main()