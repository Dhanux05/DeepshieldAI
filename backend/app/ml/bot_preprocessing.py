"""
Feature engineering for the XGBoost bot-vs-human account classifier.

This is the single source of truth for turning a raw account-metadata dict
into the numeric vector the model actually sees. `train_bot_detector.py`
(training) and `bot_detector.py` (serving) both import `extract_features`
and `FEATURE_ORDER` from here — exactly the same discipline this project
already uses for Image/Audio/Text preprocessing (see those modules'
docstrings): if training and serving ever computed features differently,
the model would score confident nonsense on every real request while
looking perfect in the training notebook.

Design decisions worth reading before touching this file:

1. ACCOUNT AGE IS RELATIVE TO A "SNAPSHOT TIME", NOT A FIXED CONSTANT.
   `extract_features` takes an explicit `reference_date` rather than calling
   `datetime.now()` internally. Training passes the dataset's own latest
   `created_at` (the approximate moment the dataset was collected, ~2017);
   serving passes the real current time. This keeps "account age at the
   moment it was observed" a *consistent* feature definition across both —
   a 3-year-old account looked the same to the model in 2017 as a 3-year-old
   account looks in 2026. Hardcoding either side to a fixed date would have
   silently skewed every live prediction (every account in 2026 would look
   "impossibly old" relative to 2017-era training data).

2. "SENTIMENT" HERE MEANS BIO SENTIMENT, NOT TWEET SENTIMENT. The source
   dataset's `status` column is a raw, inconsistently-formatted dump of a
   single old tweet object (mixed Python-dict-repr and even raw object
   memory addresses in some rows — not reliably parseable, and not
   representative of an account's overall posting behaviour anyway, since
   it's only ever one tweet). We score sentiment on the profile `description`
   (bio) instead, using VADER (tuned for short, informal social-media text).
   This is disclosed here explicitly and again in scripts/train_bot_detector.py's
   report, matching this project's practice of documenting real model
   limitations rather than hiding them (see review_detector.py, ImageDetector
   docs in docs/MODELS.md).

3. Every raw field is read defensively. Real account dumps contain the
   literal string "None", empty strings, and missing keys interchangeably
   with actual nulls — the source CSV itself has all three. A single bad
   field must never crash inference for an otherwise-valid account.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

# Imported lazily inside functions that need it (vaderSentiment) so that
# importing this module for feature-order metadata alone never requires the
# dependency to be installed.

#: Fixed, ordered list of engineered feature names. This exact order is what
#: gets written to feature_schema.json at training time and read back at
#: serve time to build the input vector — changing the order (or adding a
#: feature) without retraining WILL silently misalign every prediction.
FEATURE_ORDER: list[str] = [
    "followers_count_log",
    "friends_count_log",
    "followers_friends_ratio",
    "listed_count_log",
    "favourites_count_log",
    "statuses_count_log",
    "account_age_days",
    "posts_per_day",
    "verified",
    "default_profile",
    "default_profile_image",
    "has_extended_profile",
    "screen_name_length",
    "screen_name_digit_ratio",
    "name_digit_count",
    "description_length",
    "description_has_url",
    "description_has_hashtag",
    "description_sentiment",
    "has_profile_url",
]

_URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
_HASHTAG_PATTERN = re.compile(r"#\w+")
_DIGIT_PATTERN = re.compile(r"\d")

#: Twitter's classic API datetime format, e.g. "Mon Jan 02 02:25:26 +0000 2017".
_TWITTER_DATETIME_FORMAT = "%a %b %d %H:%M:%S %z %Y"


def _safe_int(value, default: int = 0) -> int:
    """Coerce a raw field to int, tolerating None, '', 'None', and floats."""
    if value is None:
        return default
    if isinstance(value, float) and value != value:  # NaN
        return default
    try:
        text = str(value).strip()
        if text == "" or text.lower() == "none":
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _safe_bool_to_int(value, default: int = 0) -> int:
    """Coerce a raw field to 0/1, tolerating real bools, 'True'/'False', NaN."""
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return default
    if isinstance(value, float) and value != value:  # NaN
        return default
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return 1
    if text in ("false", "0", "no", "none", ""):
        return 0
    return default


def _safe_str(value) -> str:
    """Coerce a raw field to a plain string, tolerating None/NaN/'None'."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    text = str(value).strip()
    if text.lower() == "none":
        return ""
    # The source CSV quotes some string fields (e.g. `"Houston, TX"`); strip
    # a single layer of surrounding quotes if present so length/regex
    # features aren't thrown off by punctuation that isn't really there.
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text


def parse_account_datetime(value) -> datetime | None:
    """
    Parse `created_at` in whichever of the two formats this dataset mixes:
    Twitter's own API format, or a locale-ambiguous slash-separated one.
    Returns None (never raises) if the value can't be parsed at all — the
    caller imputes a fallback rather than losing the whole account.
    """
    text = _safe_str(value)
    if not text:
        return None

    try:
        return datetime.strptime(text, _TWITTER_DATETIME_FORMAT)
    except ValueError:
        pass

    try:
        from dateutil import parser as date_parser

        parsed = date_parser.parse(text, dayfirst=False)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, OverflowError, TypeError):
        return None


def _bio_sentiment(description: str) -> float:
    """VADER compound sentiment score in [-1, 1]; 0.0 for an empty bio."""
    if not description:
        return 0.0

    analyzer = _get_sentiment_analyzer()
    return float(analyzer.polarity_scores(description)["compound"])


_SENTIMENT_ANALYZER = None


def _get_sentiment_analyzer():
    """Lazily construct and cache the VADER analyzer (loads a small lexicon)."""
    global _SENTIMENT_ANALYZER
    if _SENTIMENT_ANALYZER is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _SENTIMENT_ANALYZER = SentimentIntensityAnalyzer()
    return _SENTIMENT_ANALYZER


def extract_features(
    account: dict,
    reference_date: datetime,
    account_age_fallback_days: float = 0.0,
) -> dict[str, float]:
    """
    Turn one raw account-metadata dict into the fixed-order feature dict.

    `account` is expected to look like one row of the training CSV / one
    account-detail JSON upload: followers_count, friends_count,
    listed_count, favourites_count, statuses_count, created_at, verified,
    default_profile, default_profile_image, has_extended_profile,
    screen_name, name, description, url. Every key is optional — a missing
    or malformed field degrades to a neutral default rather than raising,
    because a live upload will never be as clean as the training CSV.

    `reference_date` is the "now" account age is computed against — see
    module docstring, decision (1). Must be timezone-aware.

    `account_age_fallback_days` is used when `created_at` can't be parsed
    at all (imputed at training time as the training set's median age, and
    passed through to serving via feature_schema.json so a malformed
    timestamp degrades gracefully instead of raising).
    """
    followers_count = _safe_int(account.get("followers_count"))
    friends_count = _safe_int(account.get("friends_count"))
    listed_count = _safe_int(account.get("listed_count"))
    favourites_count = _safe_int(
        account.get("favourites_count", account.get("favorites_count"))
    )
    statuses_count = _safe_int(account.get("statuses_count"))

    created_at = parse_account_datetime(account.get("created_at"))
    if created_at is not None:
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)
        account_age_days = max((reference_date - created_at).total_seconds() / 86400.0, 0.0)
    else:
        account_age_days = account_age_fallback_days

    posts_per_day = statuses_count / max(account_age_days, 1.0)

    screen_name = _safe_str(account.get("screen_name"))
    name = _safe_str(account.get("name"))
    description = _safe_str(account.get("description"))
    url = _safe_str(account.get("url"))

    screen_name_digits = len(_DIGIT_PATTERN.findall(screen_name))

    return {
        "followers_count_log": math.log1p(max(followers_count, 0)),
        "friends_count_log": math.log1p(max(friends_count, 0)),
        "followers_friends_ratio": followers_count / (friends_count + 1),
        "listed_count_log": math.log1p(max(listed_count, 0)),
        "favourites_count_log": math.log1p(max(favourites_count, 0)),
        "statuses_count_log": math.log1p(max(statuses_count, 0)),
        "account_age_days": account_age_days,
        "posts_per_day": posts_per_day,
        "verified": _safe_bool_to_int(account.get("verified")),
        "default_profile": _safe_bool_to_int(account.get("default_profile")),
        "default_profile_image": _safe_bool_to_int(account.get("default_profile_image")),
        "has_extended_profile": _safe_bool_to_int(account.get("has_extended_profile")),
        "screen_name_length": float(len(screen_name)),
        "screen_name_digit_ratio": screen_name_digits / max(len(screen_name), 1),
        "name_digit_count": float(len(_DIGIT_PATTERN.findall(name))),
        "description_length": float(len(description)),
        "description_has_url": float(bool(_URL_PATTERN.search(description))),
        "description_has_hashtag": float(bool(_HASHTAG_PATTERN.search(description))),
        "description_sentiment": _bio_sentiment(description),
        "has_profile_url": float(bool(url)),
    }


def features_to_vector(features: dict[str, float]) -> list[float]:
    """Flatten a features dict into FEATURE_ORDER order for the model."""
    return [features[name] for name in FEATURE_ORDER]
