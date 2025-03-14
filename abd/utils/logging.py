from abd.utils.env import env


async def send_heartbeat(heartbeat: str, messages: list[str] = []):
    if env.logging:
        msg = await env.slack_client.chat_postMessage(
            channel=env.slack_heartbeat_channel, text=heartbeat
        )
        if messages:
            for message in messages:
                await env.slack_client.chat_postMessage(
                    channel=env.slack_heartbeat_channel,
                    text=message,
                    thread_ts=msg["ts"],
                )
