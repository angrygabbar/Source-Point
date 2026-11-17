"""Regular expressions used to extract SuperCoin / CoinBack reward statements."""

import re

_I = re.IGNORECASE

COIN = r"(?:super\s?coins?|coin\s?backs?)"
RUPEE = r"(?:₹|rs\.?|inr)\s?"
AMT = r"\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?"
PCT_NUM = r"\d{1,4}(?:\.\d{1,2})?"

COIN_RE = re.compile(COIN, _I)

PCT_BEFORE_RE = re.compile(
    rf"(?P<upto>\bup\s?to\s+)?(?P<pct>{PCT_NUM})\s?%\s*(?:{COIN}|(?:back\s+)?(?:in|as)\s+{COIN})", _I
)
PCT_AFTER_RE = re.compile(
    rf"{COIN}\s*(?:back\s+)?(?:(?:of|worth)\s+|:\s*|(?=up\s?to\s))(?P<upto>up\s?to\s+)?(?P<pct>{PCT_NUM})\s?%", _I
)
RATE_RE = re.compile(
    rf"(?P<coins>{AMT})\s?{COIN}\s*(?:per|for\s+every|on\s+every|for\s+each|every|/)\s*{RUPEE}(?P<amt>{AMT})", _I
)
FIXED_RE = re.compile(rf"(?P<upto>\bup\s?to\s+)?(?<![\d.,%₹])\b(?P<coins>{AMT})\s?{COIN}", _I)
CAP_RE = re.compile(
    rf"(?:max(?:imum)?\.?(?:\s+(?:of|reward|benefit|cashback))?|capped\s+at|up\s?to\s+a\s+max(?:imum)?\s+of|limited\s+to)"
    rf"\s*(?:of\s+)?(?P<cap>{AMT})\s?{COIN}",
    _I,
)
MIN_PURCHASE_RE = re.compile(
    rf"(?:min(?:imum)?\.?\s+(?:purchase|order|cart|spend|transaction)(?:\s+(?:value|amount))?(?:\s+of)?"
    rf"|on\s+(?:a\s+)?(?:purchases?|orders?|spends?)\s+(?:above|over|worth)|orders?\s+above|spends?\s+(?:above|over))"
    rf"\s*:?\s*{RUPEE}(?P<amt>{AMT})",
    _I,
)
MAX_PURCHASE_RE = re.compile(
    rf"max(?:imum)?\.?\s+(?:purchase|order|eligible|transaction|cart)(?:\s+(?:value|amount))?(?:\s+of)?\s*:?\s*{RUPEE}(?P<amt>{AMT})",
    _I,
)
ELIGIBLE_AMOUNT_RE = re.compile(
    rf"(?:on\s+(?:a\s+)?(?:purchase|order|spend)\s+(?:value\s+)?of|eligible\s+(?:purchase|order|spend)(?:\s+(?:value|amount))?(?:\s+of|:)?)"
    rf"\s*{RUPEE}(?P<amt>{AMT})",
    _I,
)
NON_COIN_RE = re.compile(
    r"\b(?:bank\s+(?:offer|cashback|discount)|instant\s+discount|cashback\s+(?:on|with|using)|no\s+cost\s+emi"
    r"|exchange\s+offer|special\s+price|partner\s+offer)",
    _I,
)
REDEEM_RE = re.compile(
    rf"\b(?:redeem|use|using|pay\s+(?:with|using)|spend)\s+(?:your\s+|up\s?to\s+)?(?:(?:{AMT})\s?)?{COIN}", _I
)
EARN_RE = re.compile(r"\b(?:get|earn|win|back|cashback|reward|credited|receive|bonus)\b", _I)
VALIDITY_RE = re.compile(
    r"(?:valid\s+(?:till|until|up\s?to|through)|offer\s+(?:ends?|expires?)(?:\s+on)?|expires?(?:\s+on)?|ends?\s+on)\s*:?\s*"
    r"(?P<date>\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?(?:,?\s+\d{4})?"
    r"|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?"
    r"|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    _I,
)

RESTRICTION_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "payment": [
        re.compile(p, _I)
        for p in (
            r"\bupi\b", r"credit\s+cards?", r"debit\s+cards?", r"net\s?banking", r"pay\s?later", r"\bemi\b",
            r"\b(?:axis|hdfc|sbi|icici|kotak|idfc|bob|rbl|hsbc|yes|au)\s+bank\b",
        )
    ],
    "customer": [
        re.compile(p, _I)
        for p in (
            r"plus\s+members?", r"flipkart\s+plus", r"\bvip\b", r"new\s+(?:users?|customers?)",
            r"first\s+(?:order|purchase)", r"select(?:ed)?\s+(?:users?|customers?)", r"eligible\s+(?:users?|customers?)",
        )
    ],
    "seller": [re.compile(p, _I) for p in (r"select(?:ed)?\s+sellers?", r"sold\s+by\s+[A-Za-z][\w&.\- ]{2,40}")],
    "product": [re.compile(p, _I) for p in (r"select(?:ed)?\s+(?:products?|items?)", r"on\s+this\s+product")],
    "other": [
        re.compile(p, _I)
        for p in (
            r"t\s?&\s?c\s+apply", r"terms\s+(?:and|&)\s+conditions", r"once\s+per\s+(?:user|customer|account)",
            r"credited\s+(?:within|after)\s+[\w\s]{2,25}",
        )
    ],
}

SEGMENT_SPLIT_RE = re.compile(r"(?:\r?\n|•|\u2022|;|\s\|\s)+")
