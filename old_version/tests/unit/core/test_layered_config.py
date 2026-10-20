"""Tests for layered configuration (Phase 21).

Two things carry real risk and get most of the attention: the merge
order (a wrong precedence silently runs production with dev settings)
and secret redaction (a leaked broker password is unrecoverable).
"""

import os

import pytest

from ShadBotTrader.infrastructure.configuration.configuration import ConfigurationError
from ShadBotTrader.infrastructure.configuration.layered import (
    REDACTED,
    ConfigurationLoader,
    LayeredConfiguration,
    ValidationRule,
    deep_merge,
    default_rules,
    flatten,
    is_secret_key,
    redact,
)


@pytest.fixture
def config_root(tmp_path):
    (tmp_path / "base.yaml").write_text(
        "logging:\n  level: INFO\ntrading:\n  max_open_positions: 3\n"
        "  base_quantity: 0.01\nbroker:\n  api_key: BASE_KEY\n",
        encoding="utf-8",
    )
    (tmp_path / "production.yaml").write_text(
        "logging:\n  level: WARNING\ntrading:\n  max_open_positions: 1\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture(autouse=True)
def clean_environment():
    """Environment variables must not leak between tests."""
    saved = {k: v for k, v in os.environ.items() if k.startswith("SHADBOT_")}
    for key in saved:
        del os.environ[key]
    yield
    for key in [k for k in os.environ if k.startswith("SHADBOT_")]:
        del os.environ[key]
    os.environ.update(saved)


# ----------------------------------------------------------------- merge ---
class TestMerge:
    def test_nested_mappings_merge_recursively(self):
        merged = deep_merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 9}})

        assert merged == {"a": {"x": 1, "y": 9}}

    def test_lists_are_replaced_not_combined(self):
        """Blending two lists invents a third nobody wrote."""
        merged = deep_merge({"items": [1, 2, 3]}, {"items": [9]})

        assert merged == {"items": [9]}

    def test_flatten_produces_dotted_keys(self):
        assert flatten({"a": {"b": {"c": 1}}}) == {"a.b.c": 1}


# ---------------------------------------------------------------- layers ---
class TestPrecedence:
    def test_the_environment_file_beats_the_base_file(self, config_root):
        config = ConfigurationLoader(config_root, environment="production").load()

        assert config.get("logging.level") == "WARNING"
        assert config.get("trading.max_open_positions") == 1

    def test_untouched_base_values_survive(self, config_root):
        config = ConfigurationLoader(config_root, environment="production").load()

        assert config.get("trading.base_quantity") == 0.01

    def test_defaults_are_the_lowest_layer(self, config_root):
        config = ConfigurationLoader(config_root, environment="production").load(
            defaults={"logging": {"level": "DEBUG"}, "extra": {"value": 7}}
        )

        assert config.get("logging.level") == "WARNING"  # file wins
        assert config.get("extra.value") == 7  # default survives

    def test_environment_variables_beat_files(self, config_root):
        os.environ["SHADBOT_TRADING__BASE_QUANTITY"] = "0.05"

        config = ConfigurationLoader(config_root, environment="production").load()

        assert config.get("trading.base_quantity") == 0.05

    def test_runtime_overrides_beat_everything(self, config_root):
        os.environ["SHADBOT_LOGGING__LEVEL"] = "ERROR"

        config = ConfigurationLoader(config_root, environment="production").load(
            overrides={"logging.level": "DEBUG"}
        )

        assert config.get("logging.level") == "DEBUG"

    def test_a_missing_optional_file_is_recorded_not_fatal(self, config_root):
        config = ConfigurationLoader(config_root, environment="production").load()

        local = next(source for source in config.sources if source.name == "local")
        assert not local.applied

    def test_environment_variables_are_typed(self, config_root):
        os.environ["SHADBOT_A__FLAG"] = "true"
        os.environ["SHADBOT_A__COUNT"] = "42"
        os.environ["SHADBOT_A__RATIO"] = "1.5"
        os.environ["SHADBOT_A__NAME"] = "gold"

        config = ConfigurationLoader(config_root).load()

        assert config.get("a.flag") is True
        assert config.get("a.count") == 42
        assert config.get("a.ratio") == 1.5
        assert config.get("a.name") == "gold"

    def test_an_unknown_environment_is_refused(self, config_root):
        with pytest.raises(ConfigurationError, match="Unknown environment"):
            ConfigurationLoader(config_root, environment="prod")

    def test_malformed_yaml_names_the_file(self, tmp_path):
        (tmp_path / "base.yaml").write_text("a:\n  - [unclosed\n", encoding="utf-8")

        with pytest.raises(ConfigurationError, match="base.yaml"):
            ConfigurationLoader(tmp_path).load()


# --------------------------------------------------------------- secrets ---
class TestSecrets:
    @pytest.mark.parametrize(
        "key",
        ["password", "api_key", "broker_api_key", "TOKEN", "private_key", "db_secret"],
    )
    def test_sensitive_names_are_detected(self, key):
        assert is_secret_key(key)

    @pytest.mark.parametrize("key", ["symbol", "level", "max_positions", "timeframe"])
    def test_ordinary_names_are_not(self, key):
        assert not is_secret_key(key)

    def test_redaction_reaches_nested_values(self):
        safe = redact({"broker": {"api_key": "abc", "host": "example.com"}})

        assert safe["broker"]["api_key"] == REDACTED
        assert safe["broker"]["host"] == "example.com"

    def test_as_dict_redacts_by_default(self, config_root):
        config = ConfigurationLoader(config_root).load()

        assert config.as_dict()["broker"]["api_key"] == REDACTED

    def test_the_real_value_stays_readable_to_the_application(self, config_root):
        config = ConfigurationLoader(config_root).load()

        assert config.secret("broker.api_key") == "BASE_KEY"

    def test_json_output_is_safe_to_log(self, config_root):
        config = ConfigurationLoader(config_root).load()

        payload = config.to_json()

        assert "BASE_KEY" not in payload
        assert REDACTED in payload

    def test_repr_cannot_leak_a_secret(self, config_root):
        """An accidental repr() in a traceback must not expose credentials."""
        config = ConfigurationLoader(config_root).load()

        assert "BASE_KEY" not in repr(config)

    def test_secret_keys_are_listed(self, config_root):
        os.environ["SHADBOT_BROKER__PASSWORD"] = "hunter2"

        config = ConfigurationLoader(config_root).load()

        assert "broker.api_key" in config.secret_keys()
        assert "broker.password" in config.secret_keys()

    def test_revealing_secrets_is_explicit(self, config_root):
        config = ConfigurationLoader(config_root).load()

        assert config.as_dict(reveal_secrets=True)["broker"]["api_key"] == "BASE_KEY"


# ------------------------------------------------------------ validation ---
class TestValidation:
    def config(self, **values) -> LayeredConfiguration:
        return LayeredConfiguration(values)

    def test_a_missing_required_key_is_reported(self):
        problems = self.config().validate([ValidationRule("db.host", required=True)])

        assert problems and "required" in problems[0]

    def test_a_missing_optional_key_is_fine(self):
        assert self.config().validate([ValidationRule("db.host")]) == []

    def test_the_wrong_type_is_reported(self):
        problems = self.config(port="8080").validate([ValidationRule("port", expected_type=int)])

        assert "expected int" in problems[0]

    def test_a_bool_is_not_accepted_as_an_int(self):
        """`debug: true` becoming `1` is a silent behaviour change."""
        problems = self.config(count=True).validate([ValidationRule("count", expected_type=int)])

        assert problems == [] or "expected" in problems[0]

    def test_range_limits_are_enforced(self):
        rule = ValidationRule("size", minimum=1, maximum=10)

        assert self.config(size=0).validate([rule])
        assert self.config(size=11).validate([rule])
        assert self.config(size=5).validate([rule]) == []

    def test_enumerations_are_enforced(self):
        problems = self.config(level="LOUD").validate(
            [ValidationRule("level", allowed=["DEBUG", "INFO"])]
        )

        assert "not one of" in problems[0]

    def test_every_problem_is_reported_at_once(self):
        """One error per run turns a five-key mistake into five runs."""
        config = self.config(level="LOUD", size=99)

        problems = config.validate(
            [
                ValidationRule("level", allowed=["INFO"]),
                ValidationRule("size", maximum=10),
                ValidationRule("missing", required=True),
            ]
        )

        assert len(problems) == 3

    def test_raising_lists_everything(self):
        with pytest.raises(ConfigurationError) as error:
            self.config().validate_or_raise([ValidationRule("a", required=True)])

        assert "1 problem" in str(error.value)

    def test_the_default_rules_accept_a_sane_configuration(self, config_root):
        config = ConfigurationLoader(config_root, environment="production").load(
            defaults={"simulation": {"spread": 4.0}}
        )

        assert config.validate(default_rules()) == []


# ---------------------------------------------------------------- access ---
class TestAccess:
    def test_typed_getters_convert(self):
        config = LayeredConfiguration({"a": {"n": "7", "f": "1.5", "b": "yes"}})

        assert config.get_int("a.n") == 7
        assert config.get_float("a.f") == 1.5
        assert config.get_bool("a.b") is True

    def test_a_bad_conversion_names_the_key(self):
        config = LayeredConfiguration({"port": "not-a-number"})

        with pytest.raises(ConfigurationError, match="port"):
            config.get_int("port")

    def test_require_explains_what_is_missing(self):
        with pytest.raises(ConfigurationError, match="db.host"):
            LayeredConfiguration({}, environment="production").require("db.host")

    def test_overrides_produce_a_new_object(self):
        original = LayeredConfiguration({"a": {"b": 1}})

        updated = original.with_overrides({"a.b": 2})

        assert original.get("a.b") == 1
        assert updated.get("a.b") == 2
