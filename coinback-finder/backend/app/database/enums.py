from enum import StrEnum


class OfferStatus(StrEnum):
    DETECTED = "DETECTED"
    UNVERIFIED = "UNVERIFIED"
    ACCOUNT_CHECK_REQUIRED = "ACCOUNT_CHECK_REQUIRED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


INACTIVE_OFFER_STATUSES: tuple[str, ...] = (
    OfferStatus.REJECTED,
    OfferStatus.EXPIRED,
    OfferStatus.SOURCE_UNAVAILABLE,
)
PENDING_VERIFICATION_STATUSES: tuple[str, ...] = (
    OfferStatus.DETECTED,
    OfferStatus.UNVERIFIED,
    OfferStatus.ACCOUNT_CHECK_REQUIRED,
)


class RewardType(StrEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_COINS = "FIXED_COINS"
    PER_SPEND_RATE = "PER_SPEND_RATE"
    CONDITIONAL_UP_TO = "CONDITIONAL_UP_TO"
    NOT_COINBACK = "NOT_COINBACK"


class SourceType(StrEnum):
    PUBLIC_SEARCH = "PUBLIC_SEARCH"
    USER_SUBMITTED = "USER_SUBMITTED"
    THIRD_PARTY = "THIRD_PARTY"
    PRODUCT_PAGE = "PRODUCT_PAGE"
    MANUAL = "MANUAL"


# Higher rank = stronger evidence; weaker evidence never overwrites stronger evidence.
EVIDENCE_RANK: dict[str, int] = {
    SourceType.PUBLIC_SEARCH: 1,
    SourceType.THIRD_PARTY: 2,
    SourceType.USER_SUBMITTED: 3,
    SourceType.PRODUCT_PAGE: 3,
    SourceType.MANUAL: 4,
}


class ScanStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    INTERRUPTED = "INTERRUPTED"


class ScanTrigger(StrEnum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"
    DRY_RUN = "DRY_RUN"


class NotificationEvent(StrEnum):
    NEW_OFFER = "NEW_OFFER"
    OFFER_CHANGED = "OFFER_CHANGED"
    OFFER_EXPIRING = "OFFER_EXPIRING"
    TEST = "TEST"


class AccessStatus(StrEnum):
    PENDING = "PENDING"
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"
    NOT_PERMITTED = "NOT_PERMITTED"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ACCOUNT_CHECK_REQUIRED = "ACCOUNT_CHECK_REQUIRED"
