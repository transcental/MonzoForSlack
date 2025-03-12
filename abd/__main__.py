import asyncio
import contextlib
import logging

import uvicorn
from aiohttp import ClientSession
from dotenv import load_dotenv
from starlette.applications import Starlette

from abd.utils.env import env
from abd.utils.logging import send_heartbeat

load_dotenv()

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

logging.basicConfig(level="INFO")


@contextlib.asynccontextmanager
async def main(_app: Starlette):
    await send_heartbeat(":ac-bells: ADB is online!")
    async with ClientSession() as session:
        env.session = session
        env.monzo_client.session = session

        auth = await env.monzo_client.test_auth()
        if not auth:
            await env.slack_client.chat_postMessage(
                channel=env.slack_user_id,
                text=f":x: Monzo authentication failed. Please re-authenticate <{env.monzo_client.generate_monzo_url()}|here>.",
            )
    yield


def start():
    uvicorn.run(
        "abd.utils.starlette:app",
        host="0.0.0.0",
        port=env.port,
        log_level="info" if env.environment != "production" else "warning",
    )


if __name__ == "__main__":
    start()
