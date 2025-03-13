from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from abd.__main__ import main
from abd.utils.env import env
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
    match type:
        case "transaction.created":
            amount = data.get("amount")
            merchant = data.get("merchant")
            icon = merchant.get("logo")
            emoji = merchant.get("emoji")
            name = merchant.get("name")
            currency = data.get("currency")
            category = data.get("category")
            address = merchant.get("address", {})
            city = address.get("city")
            country = address.get("country")

            action = "spent" if amount < 0 else "received"
            amount = abs(amount)
            symbol = ""

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

            await env.slack_client.chat_postMessage(
                text=f"{emoji} <@{env.slack_user_id}> {action} *{symbol}{amount / 100}* {'with' if action == 'spent' else 'from'} *{name}* in {city}, {country} on {category}",
                channel=env.slack_log_channel,
                icon_url=icon,
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
