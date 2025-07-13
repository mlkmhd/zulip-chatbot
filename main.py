import html2text
from zulip_tools import *
from gitlab_tools import *
from config import *


help_message = ("**Available commands:** \n\n**1- prints list of commands** \n/help"
                "\n\n**2- deploy a version to an environment:**"
                "\n/deploy\nenv: [dev, sandbox, prod] \nversion: 1.2.3"
                "\n\n**3- prints the current deployed version in an environment:**"
                "\n/deployed-version \nenv: [dev, sandbox, prod]"
                "\n\n**4- prints the list of available versions exist in the repository:**"
                "\n/versions"
                "\n\n**5- prints the list of environment:**"
                "\n/envs"
                "\n\n**6- replicate a package from an repository to another repository**"
                "\n/replicate-package {source} {destination} {version}")

def main():
    last_id = get_last_message_id()

    while True:
        messages = get_new_messages(anchor=last_id+1)
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
                    send_message(STREAM_NAME, topic_name, "I got your order, I'll prepare the Merge Request and send you the link.\n please wait some seconds...")
                    pipeline_id = trigger_gitlab_pipeline(topic_name, content)
                    status, result = get_result_from_pipeline(285, pipeline_id)
                    if status == "ok":
                        send_message(STREAM_NAME, topic_name, "the Merge Request has been created: \n"+ result+ " \nyou can review and merge it")
                    else:
                        send_message(STREAM_NAME, topic_name, "failed to create the Merge Request. "+ result)
                elif content.startswith("/deployed-version"):
                    send_message(STREAM_NAME, topic_name, "not implemented yet")
                elif content.startswith("/versions"):
                    send_message(STREAM_NAME, topic_name, "not implemented yet")
                elif content.startswith("/envs"):
                    send_message(STREAM_NAME, topic_name, "not implemented yet")
                else:
                    send_message(STREAM_NAME, topic_name, "your command not found!")
                    send_message(STREAM_NAME, topic_name, help_message)

            last_id = max(last_id, msg_id)
            save_last_message_id(last_id)

        time.sleep(5)  # wait 5 seconds and re-pull again

if __name__ == "__main__":
    main()