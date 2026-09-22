"""
Regression coverage for app/ml/bot_preprocessing.py's extract_features().

This is the single source of truth both scripts/train_bot_detector.py
(training) and app/ml/bot_detector.py (serving) import from — see that
module's own docstring on why training/serving must compute features
identically. These tests pin down the exact behaviour this session already
verified by hand against the real "Analyze an account" payload shape before
Phase 10 shipped: every FEATURE_ORDER key is produced, malformed/missing
input degrades to a neutral default instead of raising, and the two
declared, disclosed modelling caveats (bio sentiment vs. tweet sentiment;
Twitter-shaped features only) stay true to their own docstring.
"""
from datetime import datetime, timezone

from app.ml.bot_preprocessing import (
    FEATURE_ORDER,
    extract_features,
    features_to_vector,
    parse_account_datetime,
)

REFERENCE_DATE = datetime(2026, 9, 1, tzinfo=timezone.utc)

# Matches exactly what the frontend's "Analyze an account" form
# (Upload.jsx's ACCOUNT_FORM_DEFAULTS) posts as document_type="Account".
REALISTIC_ACCOUNT_PAYLOAD = {
    "screen_name": "example_user42",
    "name": "Example User",
    "description": "Just here for the memes. https://example.com #crypto",
    "url": "https://example.com",
    "created_at": "Mon Jan 02 02:25:26 +0000 2017",
    "followers_count": 1500,
    "friends_count": 300,
    "listed_count": 12,
    "favourites_count": 4200,
    "statuses_count": 8900,
    "verified": False,
    "default_profile": False,
    "default_profile_image": False,
    "has_extended_profile": True,
}


def test_extract_features_produces_every_declared_feature_in_order():
    features = extract_features(REALISTIC_ACCOUNT_PAYLOAD, reference_date=REFERENCE_DATE)

    assert set(features.keys()) == set(FEATURE_ORDER)
    for value in features.values():
        assert isinstance(value, (int, float))


def test_features_to_vector_matches_feature_order():
    features = extract_features(REALISTIC_ACCOUNT_PAYLOAD, reference_date=REFERENCE_DATE)
    vector = features_to_vector(features)

    assert vector == [features[name] for name in FEATURE_ORDER]
    assert len(vector) == len(FEATURE_ORDER)


def test_extract_features_flags_url_and_hashtag_in_bio():
    features = extract_features(REALISTIC_ACCOUNT_PAYLOAD, reference_date=REFERENCE_DATE)

    assert features["description_has_url"] == 1.0
    assert features["description_has_hashtag"] == 1.0
    assert features["has_profile_url"] == 1.0


def test_extract_features_tolerates_missing_and_malformed_fields():
    """
    Real account dumps mix None, "", and the literal string "None"
    interchangeably (see the module docstring's decision 3) — a single bad
    field must never crash inference for an otherwise-valid account.
    """
    messy_payload = {
        "screen_name": None,
        "name": "",
        "description": "None",
        "followers_count": "None",
        "friends_count": "",
        "statuses_count": float("nan"),
        "created_at": "not a real date",
        "verified": "maybe",  # neither a recognised true/false token
    }

    # Must not raise.
    features = extract_features(
        messy_payload, reference_date=REFERENCE_DATE, account_age_fallback_days=365.0
    )

    assert features["followers_count_log"] == 0.0
    assert features["screen_name_length"] == 0.0
    assert features["description_length"] == 0.0
    # created_at couldn't be parsed -> falls back to the supplied default
    # rather than raising or silently becoming a huge/negative age.
    assert features["account_age_days"] == 365.0
    # An unrecognised truthy/falsy token defaults to 0, not True.
    assert features["verified"] == 0


def test_extract_features_handles_a_completely_empty_account():
    features = extract_features({}, reference_date=REFERENCE_DATE)

    assert features["account_age_days"] == 0.0
    assert features["followers_friends_ratio"] == 0.0  # 0 / (0 + 1)
    assert features["description_sentiment"] == 0.0  # neutral for an empty bio


def test_parse_account_datetime_accepts_the_twitter_api_format():
    parsed = parse_account_datetime("Mon Jan 02 02:25:26 +0000 2017")

    assert parsed is not None
    assert parsed.year == 2017
    assert parsed.month == 1


def test_parse_account_datetime_returns_none_for_garbage_instead_of_raising():
    assert parse_account_datetime("definitely not a date") is None
    assert parse_account_datetime(None) is None
    assert parse_account_datetime("") is None
