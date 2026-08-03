"""Ticker-mention extraction from free-text news bodies.

Split deliberately into a pure part (``normalize_tokens``, the regex, the
alias map -- standard library only) and an impure part (``get_tickers_count``,
which needs NLTK's WordNet corpus) so the normalization logic can be
unit-tested (see ``pipeline/tests/test_text_processing.py``) without a
network call, following the same pure-vs-framework split used throughout
``dashboard/`` (see that package's README for the rationale).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

_CLEAN_PATTERN = re.compile(r"http\S+|[^a-zA-Z\s]")

# Maps common full names to the ticker symbol used throughout the pipeline
# and dashboard (lowercase, matching Config.TARGET_TICKERS).
ALIAS_MAP: dict[str, str] = {
    "bitcoin": "btc",
    "ethereum": "eth",
    "ripple": "xrp",
    "solana": "sol",
    "cardano": "ada",
}

_lemmatizer = None  # lazily initialized; first use downloads the WordNet corpus


def _ensure_nltk_data() -> None:
    """Download the WordNet corpus if it isn't already present locally. Network I/O."""
    import nltk

    nltk.download(["wordnet", "omw-1.4"], quiet=True)


def _get_lemmatizer():
    """Lazily construct and cache the WordNet lemmatizer.

    Deferred past import time (unlike the original script, which called
    ``nltk.download`` as a module-level side effect) so importing this
    module -- e.g. to unit-test ``normalize_tokens`` -- never requires
    network access.
    """
    global _lemmatizer
    if _lemmatizer is None:
        _ensure_nltk_data()
        from nltk.stem import WordNetLemmatizer

        _lemmatizer = WordNetLemmatizer()
    return _lemmatizer


def normalize_tokens(tokens: Iterable[str], target_tickers: Iterable[str]) -> list[str]:
    """Map already-lemmatized lowercase tokens to canonical ticker symbols.

    Pure function (no I/O), so it's directly unit-testable without NLTK's
    corpus data being present. Tokens that don't resolve to one of
    ``target_tickers`` (via ``ALIAS_MAP`` or as-is) are dropped.
    """
    targets = set(target_tickers)
    normalized = (ALIAS_MAP.get(tok, tok) for tok in tokens)
    return [tok for tok in normalized if tok in targets]


def get_tickers_count(text: str, target_tickers: Iterable[str]) -> dict[str, int]:
    """Extract and count normalized crypto-ticker mentions from free text.

    Strips URLs and non-alphabetic characters, lemmatizes each remaining
    token (so "Bitcoin's"/"bitcoins" collapse to the same alias-mapped form
    as "bitcoin"), then keeps only tokens that resolve to one of
    ``target_tickers``. Requires the NLTK WordNet corpus, downloaded on
    first use via ``_ensure_nltk_data``.
    """
    lemmatizer = _get_lemmatizer()
    clean_text = _CLEAN_PATTERN.sub("", str(text).lower())
    lemmas = (lemmatizer.lemmatize(w) for w in clean_text.split())
    matched = normalize_tokens(lemmas, target_tickers)
    return dict(Counter(matched))
