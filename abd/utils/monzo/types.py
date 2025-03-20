from enum import Enum

from abd.utils.env import env


class TransactionSchemes(Enum):
    Mastercard = "mastercard"
    P2PPayment = "p2p_payment"
    FasterPayments = "payport_faster_payments"
    Bacs = "bacs"


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


class Mastercard:
    def __init__(self, data):
        self.id = data.get("id", "mastercard-tx")
        self.raw_amount = data.get("local_amount", 0)
        self.amount = abs(self.raw_amount)
        self.currency = data.get("local_currency", "GBP")
        self.merchant = data.get("merchant", {})
        self.merchant_name = self.merchant.get("name", "Mystery Place")
        self.merchant_category = data.get("category", "Unknown").title()
        self.merchant_address = self.merchant.get("address", {})
        self.merchant_city = self.merchant_address.get("city", "").title()
        self.merchant_country = self.merchant_address.get("country", "Unknown").title()
        self.icon = self.merchant.get("logo", None)
        self.emoji = data.get("emoji", ":ac--item-bellcoin:")

        self.action = "spent" if self.raw_amount < 0 else "received"
        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            round(self.amount, 2)
        )
        self.region_str = (
            f" in {self.merchant_city}, {self.merchant_country}"
            if self.merchant_city and self.merchant_country
            else ""
        )
        self.cat_str = f" on {self.merchant_category}" if self.merchant_category else ""
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}*{self.region_str}{self.cat_str}"
        self.name = self.merchant_name


class P2PPayment:
    def __init__(self, data):
        self.id = data.get("id", "p2p-tx")
        self.raw_amount = data.get("local_amount", 0)
        self.amount = abs(self.raw_amount)
        self.currency = data.get("local_currency", "GBP")

        self.emoji = data.get("emoji", ":ac--item-bellcoin:")
        self.icon = None

        self.action = "sent" if self.raw_amount < 0 else "received"
        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            round(self.amount, 2)
        )
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {'from' if self.raw_amount > 0 else 'to'} {'a greedy person' if self.raw_amount < 0 else 'a kind person'} through :monzo-pride: Monzo"
        self.name = "Monzo Transfer"


class FasterPayments:
    def __init__(self, data):
        self.id = data.get("id", "fp-tx")
        self.raw_amount = data.get("local_amount", 0)
        self.amount = abs(self.raw_amount)
        self.currency = data.get("local_currency", "GBP")

        self.emoji = data.get("emoji", ":money_tub:")
        self.icon = None

        self.action = "sent" if self.raw_amount < 0 else "received"
        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            round(self.amount, 2)
        )
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {'from' if self.raw_amount > 0 else 'to'} {'a greedy person' if self.raw_amount < 0 else 'a kind person'} in the :flag-gb: UK"
        self.name = "Faster Payments"


class Bacs:
    def __init__(self, data):
        self.id = data.get("id", "bacs-tx")
        self.raw_amount = data.get("local_amount", 0)
        self.amount = abs(self.raw_amount)
        self.currency = data.get("local_currency", "GBP")

        self.emoji = data.get("emoji", ":money_with_wings:")
        self.icon = None

        self.action = "sent" if self.raw_amount < 0 else "received"
        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            round(self.amount, 2)
        )
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {'from' if self.raw_amount > 0 else 'to'} {'a greedy person' if self.raw_amount < 0 else 'a kind person'} in the :flag-gb: UK"
        self.name = "Bacs"


class UnknownTransaction:
    def __init__(self, data):
        self.id = data.get("id", "unknown-tx")
        self.raw_amount = data.get("local_amount", 0)
        self.amount = abs(self.raw_amount)
        self.currency = data.get("local_currency", "GBP")

        self.emoji = data.get("emoji", ":ac--item-bellcoin:")
        self.icon = None

        self.action = "sent" if self.raw_amount < 0 else "received"
        self.amount_str = CURRENCIES.get(self.currency, f"{self.currency} {{}}").format(
            round(self.amount, 2)
        )
        self.sentence = f"{self.emoji} <@{env.slack_user_id}> {self.action} *{self.amount_str}* {'from' if self.raw_amount > 0 else 'to'} {'a greedy person' if self.raw_amount < 0 else 'a kind person'}"
        self.scheme = data.get("scheme", "Monzo").title()
        self.name = f"{self.scheme} Transaction"
