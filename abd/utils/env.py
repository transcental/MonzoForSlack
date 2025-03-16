import os

from aiohttp import ClientSession
from dotenv import load_dotenv
from slack_sdk.web.async_client import AsyncWebClient

from abd.utils.monzo.handler import MonzoHandler

load_dotenv()


class Environment:
    def __init__(self):
        self.slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "unset")
        self.slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "unset")

        self.slack_log_channel = os.environ.get("SLACK_LOG_CHANNEL", "unset")
        self.slack_user_id = os.environ.get("SLACK_USER_ID", "unset")

        self.monzo_client_id = os.environ.get("MONZO_CLIENT_ID", "unset")
        self.monzo_client_secret = os.environ.get("MONZO_CLIENT_SECRET", "unset")
        self.domain = os.environ.get("DOMAIN", "unset")
        self.webhook_verif = os.environ.get("WEBHOOK_VERIF", "unset")

        self.environment = os.environ.get("ENVIRONMENT", "development")

        self.port = int(os.environ.get("PORT", 3000))
        self.logging = True if os.environ.get("LOGGING") else False

        self.slack_heartbeat_channel = os.environ.get("SLACK_HEARTBEAT_CHANNEL")

        unset = [key for key, value in self.__dict__.items() if value == "unset"]

        if unset:
            raise ValueError(f"Missing environment variables: {', '.join(unset)}")

        self.session: ClientSession

        self.monzo_client = MonzoHandler(
            client_id=self.monzo_client_id,
            client_secret=self.monzo_client_secret,
            domain=self.domain,
            webhook_verification=self.webhook_verif,
        )
        self.slack_client = AsyncWebClient(token=self.slack_bot_token)


env = Environment()
