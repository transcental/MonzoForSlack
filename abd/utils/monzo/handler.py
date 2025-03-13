import binascii
import logging
import os
from typing import Any
from typing import Optional

from aiohttp import ClientSession


BASE = "https://api.monzo.com"


class MonzoHandler:
    def __init__(self, client_id: str, client_secret: str, domain: str) -> None:
        self.state: Optional[str] = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = f"{domain}/monzo/callback"
        self.domain = domain
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

    async def post(
        self, path: str, data: dict = {}, no_auth: bool = False
    ) -> tuple[Any, int]:
        if not no_auth:
            data["Authorization"] = f"Bearer {self.access_token}"
        async with self.session.post(f"{BASE}/{path}", data=data) as res:
            if res.status == 401:
                await self.refresh_access_token()
                if not no_auth:
                    data["Authorization"] = f"Bearer {self.access_token}"
                async with self.session.post(f"{BASE}/{path}", data=data) as res:
                    json = await res.json()
                    return json, res.status
            json = await res.json()
            return json, res.status

    async def get(self, path: str, headers: dict = {}) -> tuple[Any, int]:
        headers["Authorization"] = f"Bearer {self.access_token}"
        async with self.session.get(f"{BASE}/{path}", headers=headers) as res:
            if res.status == 401:
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                async with self.session.get(f"{BASE}/{path}", headers=headers) as res:
                    json = await res.json()
                    return json, res.status
            # check mimetype
            if "application/json" not in res.headers.get("Content-Type", ""):
                text = await res.text()
                logging.warn("Monzo API returned non-JSON response.", [text])
                return text, res.status
            json = await res.json()
            return json, res.status

    async def put(self, path: str, data: dict = {}) -> tuple[Any, int]:
        data["Authorization"] = f"Bearer {self.access_token}"
        async with self.session.put(f"{BASE}/{path}", data=data) as res:
            if res.status == 401:
                await self.refresh_access_token()
                data["Authorization"] = f"Bearer {self.access_token}"
                async with self.session.put(f"{BASE}/{path}", data=data) as res:
                    json = await res.json()
                    return json, res.status
            json = await res.json()
            return json, res.status

    async def delete(self, path: str, data: dict = {}) -> tuple[Any, int]:
        data["Authorization"] = f"Bearer {self.access_token}"
        async with self.session.delete(f"{BASE}/{path}", data=data) as res:
            if res.status == 401:
                await self.refresh_access_token()
                data["Authorization"] = f"Bearer {self.access_token}"
                async with self.session.delete(f"{BASE}/{path}", data=data) as res:
                    json = await res.json()
                    return json, res.status
            json = await res.json()
            return json, res.status

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
        if status != 200:
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
        return True

    async def logout(self) -> bool:
        _res, status = await self.post("oauth2/logout")
        return status == 200

    async def test_auth(self) -> bool:
        _res, status = await self.get("ping/whoami")
        return status == 200

    async def check_webhooks(self) -> None:
        res, _status = await self.get("webhooks")
        webhooks = res.get("webhooks", [])
        found = False
        for webhook in webhooks:
            if webhook.get("url") == f"{self.domain}/monzo/webhook":
                found = True
                break
        if found:
            return
        _res, status = await self.post(
            "webhooks",
            data={"account_id": self.user_id, "url": f"{self.domain}/monzo/webhook"},
        )
        if status != 200:
            await self.check_webhooks()

    async def get_pots(self) -> list[dict]:
        res, _status = await self.get("pots")
        return res.get("pots", [])

    async def get_pot(self, id: str) -> Optional[dict]:
        res, _status = await self.get_pots()
        for pot in res:
            if pot.get("id") == id:
                return pot
        return None
