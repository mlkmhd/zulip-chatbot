# Zulip ChatOps bot
this repository is a sample bot for handling commands received from Zulip messanger to improve devops automation.

## Usage
you can run and use this project using the following commands:
```commandline
   $ cp .env.example .env
   $ docker-compose up -d
```
you need to modify the `.env` file based on your environment. 


## AirGapped Installation
run the following commands to download and save it:
```bash
$ docker pull mlkmhd/zulip-chatbot
$ docker save mlkmhd/zulip-chatbot | gzip > zulip-chatbot-docker-image.tar.gz
```

the transfer the `zulip-chatbot-docker-image.tar.gz` file to the server and run the following commands:

```bash
$ docker load -i zulip-chatbot-docker-image.tar.gz
Loaded image: mlkmhd/zulip-chatbot:latest
Loaded image ID: sha256:e1acedb25ddd8ad1bc4dab51a8d0a4bf3ee7c1612c85cd307a16e184ee246c59
Loaded image ID: sha256:96328d55cc5cc5f68e8b4842db49762f1dfcd5fd582f66947fc81fac5af2f355
$ docker-compose up -d --force-recreate --build
```