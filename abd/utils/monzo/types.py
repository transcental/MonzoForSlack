from enum import Enum

from pydantic import BaseModel
from pydantic import ConfigDict

from abd.utils.env import env


class TransactionSchemes(Enum):
    Mastercard = "mastercard"
    P2PPayment = "p2p_payment"
    FasterPayments = "payport_faster_payments"
    Bacs = "bacs"
    PotTransfer = "uk_retail_pot"


CURRENCIES = {
    "GBP": "£{}",
    "USD": "${}",
    "EUR": "€{}",
    "JPY": "¥{}",
    "AUD": "A${}",
    "CAD": "C${}",
    "NOK": "{}kr",
    "CNY": "¥{}",
    "RMB": "¥{}",
    "SEK": "{}kr",
}


class MonzoMerchantAddressData(BaseModel):
    model_config = ConfigDict(extra="allow")
    address: str
    city: str
    country: str
    latitude: float
    longitude: float
    postcode: str
    region: str


class MonzoMerchantData(BaseModel):
    model_config = ConfigDict(extra="allow")
    address: MonzoMerchantAddressData | None
    created: str
    group_id: str
    id: str
    logo: str | None = None
    emoji: str | None = None
    name: str
    category: str


class MonzoTransactionMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str | None = None
    pot_account_id: str | None = None
    pot_id: str | None = None
    user_id: str | None = None
    trigger: str | None = None


class MonzoTransactionData(BaseModel):
    model_config = ConfigDict(extra="allow")
    account_id: str
    amount: int
    category: str
    created: str
    currency: str
    id: str
    local_amount: int
    local_currency: str
    scheme: str
    emoji: str | None = None
    settled: str
    merchant: MonzoMerchantData | None
    decline_reason: str | None = None
    metadata: MonzoTransactionMetadata | None


class MonzoResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    data: MonzoTransactionData


class BaseTransaction:
    def __init__(self, data: MonzoTransactionData):
        self.id = data.id
        self.raw_amount = data.local_amount or 0
        self.amount = abs(self.raw_amount)
        self.currency = data.local_currency
        self.scheme = data.scheme.title()
        self.category = data.category.title()

        self.emoji = data.emoji or ":ac--item-bellcoin:"
        self.merchant = data.merchant
        self.region_str = ""
        self.icon = None
        self.merchant_name = None
        self.merchant_address = None
        self.merchant_city = None
        self.merchant_country = None

        if self.merchant:
            self.icon = self.merchant.logo
            self.merchant_name = self.merchant.name
            self.merchant_address = self.merchant.address
            if self.merchant_address:
                self.merchant_city = self.merchant_address.city or ""
                self.merchant_country = self.merchant_address.country.title()
                self.region_str = (
                    f" in {self.merchant_city}, {self.merchant_country}"
                    if self.merchant_city and self.merchant_country
                    else ""
                )

        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            "{:.2f}".format(self.amount / 100)
        )

        self.spent = self.raw_amount < 0
        self.action = "spent" if self.spent else "received"

        self.display_name = self.merchant_name or "Unknown Place"
        self.direction = "from" if self.spent else "to"
        self.cat_str = f" on {self.category}" if self.category else ""
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}*{self.region_str}{self.cat_str}"


class Mastercard(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = self.merchant_name or "Mystery Place"
        self.emoji = self.emoji or ":money-printer:"


class P2PPayment(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = "Monzo Transfer"
        self.emoji = self.emoji or ":ac--item-bellcoin:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} {self.display_name} through :monzo-pride: Monzo"


class FasterPayments(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = "Faster Payments"
        self.emoji = self.emoji or ":money-tub:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} {self.display_name} in the :flag-gb: UK"


class Bacs(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = "Bacs"
        self.emoji = self.emoji or ":money_with_wings:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} {self.display_name} in the :flag-gb: UK"


class UnknownTransaction(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = f"{self.scheme} Transaction"
        self.emoji = self.emoji or ":ac--item-bellcoin:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} {self.display_name}"


class PotTransfer(BaseTransaction):
    def __init__(self, data: MonzoTransactionData, pot_info):
        super().__init__(data)
        self.name = pot_info.get("name", "Unknown Pot")
        self.emoji = self.emoji or ":potted_plant:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {'transferred' if self.raw_amount < 0 else 'withdrew'} *{self.amount_str}* {self.direction} a pot"

    @classmethod
    async def create(cls, data: MonzoTransactionData):
        metadata = data.metadata
        pot_info = {}
        if metadata:
            pot_id = metadata.pot_id
            account_id = data.account_id
            if pot_id and account_id:
                pot_info = await env.monzo_client.get_pot(pot_id, account_id) or {}

        return cls(data, pot_info)
