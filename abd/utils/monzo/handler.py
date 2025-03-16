import asyncio
import binascii
import logging
import os
from typing import Any
from typing import Optional

from aiohttp import ClientSession


BASE = "https://api.monzo.com"


class MonzoHandler:
    def __init__(
        self, client_id: str, client_secret: str, domain: str, webhook_verification: str
    ) -> None:
        self.state: Optional[str] = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = f"{domain}/monzo/callback"
        self.domain = domain
        self.webhook_verification = webhook_verification
        self.session: ClientSession

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_in: Optional[int] = None
        self.user_id: Optional[str] = None

    def generate_state(self) -> str:
        signature = binascii.hexlify(os.urandom(32))
        state = signature.decode("utf-8")
        self.state = state
        return state

    def generate_monzo_url(self) -> str:
        self.generate_state()
        return f"https://auth.monzo.com/?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={self.state}"

    async def post(self, path: str, no_auth: bool = False, **kwargs) -> tuple[Any, int]:
        headers = kwargs.pop("headers", {})

        if not no_auth:
            headers["Authorization"] = f"Bearer {self.access_token}"

        logging.info(headers, kwargs)
        try:
            async with self.session.post(
                f"{BASE}/{path}", headers=headers, **kwargs
            ) as res:
                if res.status == 401:
                    await self.refresh_access_token()
                    return await self.post(path, no_auth, **kwargs)
                elif res.status == 429:
                    logging.warning("Rate limited")
                    retry = float(res.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry)
                    return await self.post(path, no_auth, **kwargs)
                elif res.status == 403:
                    logging.error(
                        "Request authenticated but has no perms - not confirmed in app?"
                    )
                    return None, 403
                json = await res.json()
                return json, res.status
        except Exception as e:
            logging.error(f"An error occurred during POST request: {e}")
            return None, 500

    async def get(self, path: str, headers: Optional[dict] = None) -> tuple[Any, int]:
        if headers is None:
            headers = {}
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            async with self.session.get(f"{BASE}/{path}", headers=headers) as res:
                if res.status == 401:
                    await self.refresh_access_token()
                    return await self.get(path, headers)
                elif res.status == 429:
                    logging.warning("Rate limited")
                    retry = float(res.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry)
                    return await self.get(path, headers)
                elif res.status == 403:
                    logging.error(
                        "Request authenticated but has no perms - not confirmed in app?"
                    )
                    return None, 403
                json = await res.json()
                return json, res.status
        except Exception as e:
            logging.error(f"An error occurred during GET request: {e}")
            return None, 500

    async def put(self, path: str, **kwargs) -> tuple[Any, int]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            async with self.session.put(
                f"{BASE}/{path}", headers=headers, **kwargs
            ) as res:
                if res.status == 401:
                    await self.refresh_access_token()
                    return await self.put(path, **kwargs)
                elif res.status == 429:
                    retry = float(res.headers.get("Retry-After", 5))
                    logging.warning(f"Rate limited for {retry}s")
                    await asyncio.sleep(retry)
                    return await self.put(path, **kwargs)
                elif res.status == 403:
                    logging.error(
                        "Request authenticated but has no perms - not confirmed in app?"
                    )
                    return None, 403
                json = await res.json()
                return json, res.status
        except Exception as e:
            logging.error(f"An error occurred during PUT request: {e}")
            return None, 500

    async def delete(self, path: str, **kwargs) -> tuple[Any, int]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            async with self.session.delete(
                f"{BASE}/{path}", headers=headers, **kwargs
            ) as res:
                if res.status == 401:
                    await self.refresh_access_token()
                    return await self.delete(path, **kwargs)
                elif res.status == 429:
                    retry = float(res.headers.get("Retry-After", 5))
                    logging.warning(f"Rate limited for {retry}s")
                    await asyncio.sleep(retry)
                    return await self.delete(path, **kwargs)
                elif res.status == 403:
                    logging.error(
                        "Request authenticated but has no perms - not confirmed in app?"
                    )
                    return None, 403
                json = await res.json()
                return json, res.status
        except Exception as e:
            logging.error(f"An error occurred during DELETE request: {e}")
            return None, 500

    async def exchange_code(self, code: str) -> bool:
        res, status = await self.post(
            "oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
            no_auth=True,
        )
        if status == 429:
            retry = float(res.headers.get("Retry-After", 5))
            await asyncio.sleep(retry)
            return await self.exchange_code(code)
        elif status != 200:
            return False
        self.access_token = res.get("access_token")
        self.refresh_token = res.get("refresh_token")
        self.expires_in = res.get("expires_in")
        self.user_id = res.get("user_id")
        return True

    async def refresh_access_token(self) -> bool:
        res, status = await self.post(
            "oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            },
            no_auth=True,
        )
        if status != 200:
            return False
        self.access_token = res.get("access_token")
        self.refresh_token = res.get("refresh_token")
        self.expires_in = res.get("expires_in")
        self.user_id = res.get("user_id")
        logging.info("Refreshed access token")
        return True

    async def logout(self) -> bool:
        _res, status = await self.post("oauth2/logout")
        return status == 200

    async def test_auth(self) -> bool:
        _res, status = await self.get("ping/whoami")
        return status == 200

    async def check_webhooks(self) -> bool:
        res, _status = await self.get("webhooks")
        webhooks = res.get("webhooks", [])
        found = False
        url = f"{self.domain}/monzo/webhook?verif={self.webhook_verification}"
        for webhook in webhooks:
            if webhook.get("url") == url:
                found = True
                break
        if found:
            return True
        logging.info("Webhook not found, creating")
        _res, status = await self.post(
            "webhooks",
            no_auth=False,
            data={
                "account_id": self.user_id,
                "url": url,
            },
        )
        logging.info(_res, status)
        if status != 200:
            await self.check_webhooks()
        return True

    async def get_pots(self) -> list[dict]:
        res, _status = await self.get("pots")
        return res.get("pots", [])

    async def get_pot(self, id: str) -> Optional[dict]:
        res, _status = await self.get_pots()
        for pot in res:
            if pot.get("id") == id:
                return pot
        return None
