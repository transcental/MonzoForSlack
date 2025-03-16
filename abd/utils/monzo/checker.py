import asyncio

from abd.utils.env import env


async def test_auth():
    while True:
        auth = await env.monzo_client.test_auth()
        if not auth:
            await env.slack_client.chat_postMessage(
                channel=env.slack_user_id,
                text=f":x: Monzo authentication failed. Please re-authenticate <{env.monzo_client.generate_monzo_url()}|here>.",
            )
            await asyncio.sleep(100)
        res = await env.monzo_client.check_webhooks()
        if not auth and res:
            await env.slack_client.chat_postMessage(
                channel=env.slack_user_id,
                text=":white_check_mark: Authenticated successfully",
            )
        await asyncio.sleep(1200)
