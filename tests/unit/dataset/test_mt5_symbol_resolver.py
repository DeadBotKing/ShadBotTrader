"""Tests for broker symbol resolution.

Picking the wrong instrument is an expensive mistake, so the resolver has
to be predictable: it ranks candidates, explains every suggestion, and
never silently substitutes one instrument for another.
"""

from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import (
    canonical_stem,
    normalise,
    resolve,
)

BROKER = [
    "EURUSD.i",
    "XAUUSD.i",
    "XAUUSDm",
    "GBPUSD",
    "BTCUSD.raw",
    "GOLDmicro",
    "USTEC",
    "XAGUSD.i",
]


# ------------------------------------------------------------ normalise ---
def test_broker_decoration_is_stripped():
    assert normalise("XAUUSD.i") == "XAUUSD"
    assert normalise("XAUUSDm") == "XAUUSD"
    assert normalise("xauusd_pro") == "XAUUSD"
    assert normalise("EUR/USD") == "EURUSD"


def test_a_plain_symbol_survives_normalisation():
    assert normalise("XAUUSD") == "XAUUSD"


def test_known_aliases_map_onto_one_stem():
    assert canonical_stem("GOLD") == "XAUUSD"
    assert canonical_stem("GOLDmicro") == "XAUUSD"
    assert canonical_stem("SILVER") == "XAGUSD"


def test_an_unknown_instrument_keeps_its_own_name():
    """The resolver must not invent a mapping it does not have."""
    assert canonical_stem("USTEC") == "USTEC"


# -------------------------------------------------------------- resolve ---
def test_an_exact_match_wins_and_is_marked_exact():
    report = resolve("XAUUSD.i", BROKER)

    assert report.found
    assert report.best is not None
    assert report.best.name == "XAUUSD.i"
    assert report.best.is_exact
    assert report.advice() == ["Use --symbol XAUUSD.i"]


def test_a_suffixed_symbol_is_found_from_the_plain_name():
    report = resolve("XAUUSD", BROKER)

    assert report.best is not None
    assert report.best.name in {"XAUUSD.i", "XAUUSDm"}
    assert not report.best.is_exact
    assert "does not exist" in report.advice()[0]


def test_an_alias_finds_the_real_instrument():
    report = resolve("GOLD", BROKER)

    assert report.found
    names = {match.name for match in report.matches}
    assert "XAUUSD.i" in names or "GOLDmicro" in names


def test_the_shortest_name_breaks_a_score_tie():
    """Least-decorated symbol first — usually the standard account."""
    report = resolve("XAUUSD", ["XAUUSD.pro.ecn", "XAUUSDm", "XAUUSD.i"])

    assert report.best is not None
    assert report.best.name == "XAUUSDm"


def test_an_unrelated_instrument_is_not_suggested():
    report = resolve("XAUUSD", BROKER)

    names = {match.name for match in report.matches}
    assert "USTEC" not in names
    assert "GBPUSD" not in names


def test_a_missing_instrument_reports_honestly():
    report = resolve("NOPE", BROKER)

    assert not report.found
    assert report.best is None
    advice = " ".join(report.advice())
    assert "No symbol resembling" in advice
    assert "Show All" in advice


def test_an_empty_terminal_gets_specific_guidance():
    """No symbols at all means Market Watch is hiding them."""
    report = resolve("XAUUSD", [])

    assert not report.found
    assert report.searched == 0
    assert "no symbols at all" in report.advice()[0].lower()


def test_every_suggestion_carries_a_reason():
    report = resolve("XAUUSD", BROKER)

    assert report.matches
    for match in report.matches:
        assert match.reason
        assert 0 < match.score <= 100


def test_results_are_ordered_by_confidence():
    report = resolve("XAUUSD", BROKER)

    scores = [match.score for match in report.matches]
    assert scores == sorted(scores, reverse=True)


# ------------------------------------------------- corruption guards ------
def test_index_names_are_never_truncated():
    """Peeling a suffix must not eat part of a real name.

    ``USTEC`` ends in 'C' and ``US30`` is short — a naive suffix strip
    turns them into ``UST`` and breaks the lookup entirely.
    """
    for name in ("USTEC", "US30", "NAS100", "GER40"):
        assert normalise(name) == name


def test_protected_instrument_names_survive():
    """``GOLD`` ends in 'D'; truncating it would produce ``GOL``."""
    assert normalise("GOLD") == "GOLD"
    assert normalise("SILVER") == "SILVER"


def test_multi_part_decoration_is_removed():
    assert normalise("XAUUSD.pro.ecn") == "XAUUSD"


def test_unrecognised_decoration_is_left_alone():
    """Better an unresolved name than a silently wrong instrument."""
    assert normalise("XAUUSD.weird9") == "XAUUSD.WEIRD9"


def test_a_broker_prefix_is_removed():
    assert normalise("FX.EURUSD") == "EURUSD"
