from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from abd.__main__ import main
from abd.utils.env import env
from abd.utils.logging import send_heartbeat
from abd.utils.slack import app as slack_app

req_handler = AsyncSlackRequestHandler(slack_app)


async def endpoint(req: Request):
    return await req_handler.handle(req)


async def health(req: Request):
    monzo_healthy = await env.monzo_client.test_auth()
    try:
        await env.slack_client.api_test()
        slack_healthy = True
    except Exception:
        slack_healthy = False

    return JSONResponse(
        {
            "healthy": monzo_healthy and slack_healthy,
            "monzo": monzo_healthy,
            "slack": slack_healthy,
        }
    )


async def monzo_callback(req: Request):
    code = req.query_params.get("code", "")
    state = req.query_params.get("state")
    if state != env.monzo_client.state:
        return JSONResponse({"error": "Invalid state"})

    await env.monzo_client.exchange_code(code)
    return JSONResponse({"message": "Authorised"})


async def webhook(req: Request):
    data = await req.json()
    type = data.get("type")
    data = data.get("data", {})
    verif = req.query_params.get("auth")
    if verif != env.webhook_verif:
        await send_heartbeat(
            heartbeat="Invalid verification code",
            messages=[f"Code: `{verif}`\n```{data}```"],
        )
        return JSONResponse({"error": "Invalid verification code"})
    match type:
        case "transaction.created":
            raw_amount = data.get("amount")
            merchant = data.get("merchant", {}) or {}
            # Check if it's a transfer
            metadata = data.get("metadata", {}) or {}

            icon = merchant.get("logo")
            emoji = merchant.get("emoji", ":ac--item-bellcoin:")
            name = merchant.get("name", "a mystery place")
            address = merchant.get("address", {})
            city = address.get("city")
            country = address.get("country")

            currency = data.get("currency")
            category = data.get("category")
            action = "spent" if raw_amount < 0 else "received"
            amount = abs(raw_amount)

            match currency:
                case "GBP":
                    symbol = "£"
                case "USD":
                    symbol = "$"
                case "EUR":
                    symbol = "€"
                case "JPY":
                    symbol = "¥"
                case "AUD":
                    symbol = "A$"
                case "CAD":
                    symbol = "C$"
                case _:
                    symbol = currency

            amount_str = f"{symbol}{(amount / 100):.2f}"
            region_str = f" in {city}, {country}" if city and country else ""
            cat_str = f" on {category}" if category else ""

            sentence = f"{emoji} <@{env.slack_user_id}> {action} *{amount_str}*{region_str}{cat_str}"

            if metadata.get("p2p_transfer_id"):
                # P2P Transfer
                name = "Monzo Transfer"
                emoji = ":blobby-money_with_wings:"
                sentence = f"{emoji} <@{env.slack_user_id}> {'received' if raw_amount > 0 else 'sent'} a *{amount_str}* transfer {'from' if raw_amount > 0 else 'to'} {'a greedy person' if raw_amount < 0 else 'a kind person'}"

            await env.slack_client.chat_postMessage(
                text=sentence,
                channel=env.slack_log_channel,
                icon_url=icon,
                username=name,
            )
            await send_heartbeat(
                heartbeat=sentence,
                messages=[f"```{data}```"],
            )
        case _:
            await send_heartbeat(
                heartbeat=f"Unhandled webhook type: {type}",
                messages=[f"```{data}```"],
            )
    return JSONResponse({"message": "Request successfully received"})


app = Starlette(
    debug=True if env.environment != "production" else False,
    routes=[
        Route(path="/slack/events", endpoint=endpoint, methods=["POST"]),
        Route(path="/health", endpoint=health, methods=["GET"]),
        Route(path="/monzo/callback", endpoint=monzo_callback, methods=["GET"]),
        Route(path="/webhook", endpoint=webhook, methods=["POST"]),
    ],
    lifespan=main,
)
