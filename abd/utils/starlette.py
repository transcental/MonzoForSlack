from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from abd.__main__ import main
from abd.utils.env import env
from abd.utils.logging import send_heartbeat
from abd.utils.monzo.types import Bacs
from abd.utils.monzo.types import FasterPayments
from abd.utils.monzo.types import Mastercard
from abd.utils.monzo.types import P2PPayment
from abd.utils.monzo.types import TransactionSchemes
from abd.utils.monzo.types import UnknownTransaction
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

    res = await env.monzo_client.exchange_code(code)
    if not res:
        return JSONResponse({"error": "Failed to exchange code"})
    return JSONResponse({"message": "Authorised"})


async def webhook(req: Request):
    data = await req.json()
    type = data.get("type")
    data = data.get("data", {})
    verif = req.query_params.get("verif")
    if verif != env.webhook_verif:
        await send_heartbeat(
            heartbeat="Invalid verification code",
            messages=[f"Code: `{verif}`\n```{data}```"],
        )
        return JSONResponse({"error": "Invalid verification code"})
    match type:
        case "transaction.created":
            match data.get("scheme"):
                case TransactionSchemes.Mastercard:
                    transaction = Mastercard(data)
                case TransactionSchemes.P2PPayment:
                    transaction = P2PPayment(data)
                case TransactionSchemes.FasterPayments:
                    transaction = FasterPayments(data)
                case TransactionSchemes.Bacs:
                    transaction = Bacs(data)
                case _:
                    transaction = UnknownTransaction(data)
            sentence = str(transaction)

            await env.slack_client.chat_postMessage(
                text=sentence,
                channel=env.slack_log_channel,
                icon_url=transaction.icon,
                username=transaction.name,
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
