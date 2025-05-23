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
    PostOfficeDeposit = "uk_cash_deposits_post_office_banking"


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
    address: str | None
    city: str | None
    country: str | None
    region: str | None


class MonzoMerchantData(BaseModel):
    model_config = ConfigDict(extra="allow")
    address: MonzoMerchantAddressData | None
    group_id: str | None = None
    id: str
    logo: str | None = None
    emoji: str | None = None
    name: str | None = None
    category: str | None = "Unknown"


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
    category: str | None
    id: str
    local_amount: int
    local_currency: str
    currency: str
    amount: int
    scheme: str
    emoji: str | None = None
    settled: str | None
    merchant: MonzoMerchantData | None
    decline_reason: str | None = None
    metadata: MonzoTransactionMetadata | None
    notes: str | None = None


class MonzoResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    data: MonzoTransactionData


class BaseTransaction:
    def __init__(self, data: MonzoTransactionData):
        self.id = data.id
        self.raw_local_amount = data.local_amount or 0
        self.local_amount = abs(self.raw_local_amount)
        self.local_currency = data.local_currency
        self.raw_amount = data.amount or 0
        self.amount = abs(self.raw_amount)
        self.currency = data.currency

        self.scheme = data.scheme.title().replace("_", " ")
        self.category = data.category or "Unknown"
        self.category = self.category.title()

        self.emoji = None
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
            self.emoji = self.merchant.emoji or data.emoji or self.emoji
            if self.merchant_address:
                self.merchant_city = self.merchant_address.city or ""
                self.merchant_country = self.merchant_address.country or ""
                self.merchant_country = self.merchant_country.title()
                self.region_str = (
                    f" in {self.merchant_city}, {self.merchant_country}"
                    if self.merchant_city and self.merchant_country
                    else ""
                )

        self.amount_str = CURRENCIES.get(
            self.local_currency, f"{self.local_currency} {{}}"
        ).format("{:.2f}".format(self.local_amount / 100))

        if self.local_currency != self.currency:
            temp_amount_str = CURRENCIES.get(
                self.currency, f"{self.currency} {{}}"
            ).format("{:.2f}".format(self.amount / 100))
            self.amount_str += f" ({temp_amount_str})"

        self.spent = self.raw_local_amount < 0
        self.action = "spent" if self.spent else "received"

        self.display_name = self.merchant_name or "somewhere"
        self.direction = "to" if self.spent else "from"
        self.cat_str = f" on {self.category}" if self.category else ""
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}*{self.region_str}{self.cat_str}"


class Mastercard(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = self.merchant_name or "Mystery Place"
        self.emoji = self.emoji or ":money-printer:"

        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}*{self.region_str}{self.cat_str}"


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


class PostOfficeDeposit(BaseTransaction):
    def __init__(self, data: MonzoTransactionData):
        super().__init__(data)
        self.name = "Post Office Deposit"
        self.emoji = self.emoji or ":pound:"

        self.action = "deposited" if self.raw_amount > 0 else "withdrew"
        self.direction = "into" if self.raw_amount > 0 else "from"
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} their account"


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
        pot_icon = pot_info.get("cover_image_url", None)
        self.icon = (
            f"https://square.uwu.mba/square?url={pot_icon}" if pot_icon else None
        )

        self.action = "transferred" if self.raw_amount < 0 else "withdrew"
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {self.direction} a pot"

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
