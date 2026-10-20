"""Tests for structured logging (Phase 22).

The properties that matter operationally: records are machine-readable,
context follows the operation without being passed by hand, and secrets
never reach a sink.
"""

import json
import logging
import threading

import pytest

from ShadBotTrader.infrastructure.configuration.layered import (
    REDACTED,
    LayeredConfiguration,
)
from ShadBotTrader.infrastructure.logging.structured import (
    JsonFormatter,
    LogRecord,
    StructuredLogger,
    configure_from,
    configure_logging,
    correlation_scope,
    current_context,
    get_logger,
    log_context,
    new_correlation_id,
)


@pytest.fixture
def captured(tmp_path):
    """Configure logging to a file and yield a reader for the records."""
    path = tmp_path / "test.log"
    configure_logging(level="DEBUG", environment="test", json_output=True, log_file=path)

    def read():
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").strip().splitlines()
            if line
        ]

    yield read
    logging.getLogger("ShadBotTrader").handlers.clear()


# ---------------------------------------------------------------- record ---
class TestLogRecord:
    def test_the_minimum_contract_is_always_present(self):
        """§9: timestamp, level and message are mandatory."""
        payload = LogRecord(timestamp="t", level="INFO", message="hello").to_dict()

        assert payload == {"timestamp": "t", "level": "INFO", "message": "hello"}

    def test_empty_optional_fields_are_omitted(self):
        """Emitting blanks makes every line noisier without informing."""
        payload = LogRecord(timestamp="t", level="INFO", message="m").to_dict()

        assert "correlation_id" not in payload
        assert "exception" not in payload

    def test_populated_fields_appear(self):
        payload = LogRecord(
            timestamp="t",
            level="INFO",
            message="m",
            correlation_id="abc",
            component="Engine",
            metadata={"symbol": "XAUUSD"},
        ).to_dict()

        assert payload["correlation_id"] == "abc"
        assert payload["metadata"]["symbol"] == "XAUUSD"

    def test_a_record_serialises_to_one_json_line(self):
        text = LogRecord(timestamp="t", level="INFO", message="m").to_json()

        assert "\n" not in text
        assert json.loads(text)["level"] == "INFO"

    def test_the_text_form_is_readable(self):
        text = LogRecord(
            timestamp="2026-01-01T00:00:00",
            level="ERROR",
            message="failed",
            component="Engine",
        ).to_text()

        assert "ERROR" in text and "[Engine]" in text and "failed" in text


# --------------------------------------------------------------- context ---
class TestContext:
    def test_context_is_empty_by_default(self):
        assert current_context() == {}

    def test_values_are_visible_inside_the_block(self):
        with log_context(run_id="r1"):
            assert current_context()["run_id"] == "r1"

    def test_context_is_restored_afterwards(self):
        with log_context(run_id="r1"):
            pass

        assert "run_id" not in current_context()

    def test_context_is_restored_even_when_the_body_raises(self):
        """Exactly when the context matters most."""
        with pytest.raises(RuntimeError):
            with log_context(run_id="r1"):
                raise RuntimeError("boom")

        assert current_context() == {}

    def test_nested_contexts_merge(self):
        with log_context(a=1):
            with log_context(b=2):
                assert current_context() == {"a": 1, "b": 2}

    def test_an_inner_value_shadows_an_outer_one(self):
        with log_context(level="outer"):
            with log_context(level="inner"):
                assert current_context()["level"] == "inner"

    def test_correlation_ids_are_unique(self):
        assert new_correlation_id() != new_correlation_id()

    def test_a_scope_generates_an_id_when_none_is_given(self):
        with correlation_scope() as identifier:
            assert identifier
            assert current_context()["correlation_id"] == identifier

    def test_an_explicit_id_is_used_as_is(self):
        with correlation_scope("fixed-id") as identifier:
            assert identifier == "fixed-id"

    def test_context_does_not_leak_between_threads(self):
        """contextvars, not globals — the runner and bus are threaded."""
        seen = {}

        def worker():
            seen["thread"] = current_context()

        with log_context(run_id="main"):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

        assert seen["thread"] == {}


# ---------------------------------------------------------------- output ---
class TestLogging:
    def test_a_record_reaches_the_sink(self, captured):
        get_logger("test").info("hello", event="greet")

        records = captured()
        assert len(records) == 1
        assert records[0]["message"] == "hello"
        assert records[0]["event"] == "greet"

    def test_the_correlation_id_appears_on_every_record(self, captured):
        logger = get_logger("test")
        with correlation_scope("cycle-1"):
            logger.info("first")
            logger.info("second")

        records = captured()
        assert all(record["correlation_id"] == "cycle-1" for record in records)

    def test_records_outside_the_scope_have_no_correlation_id(self, captured):
        logger = get_logger("test")
        with correlation_scope("cycle-1"):
            logger.info("inside")
        logger.info("outside")

        records = captured()
        assert "correlation_id" not in records[1]

    def test_extra_fields_land_in_metadata(self, captured):
        get_logger("test").info("trade", symbol="XAUUSD", quantity=0.01)

        metadata = captured()[0]["metadata"]
        assert metadata["symbol"] == "XAUUSD"
        assert metadata["quantity"] == 0.01

    def test_secrets_are_redacted_before_reaching_the_sink(self, captured):
        """The whole point of redacting inside the logger."""
        get_logger("test").info("connecting", api_key="SECRET", password="hunter2")

        raw = json.dumps(captured()[0])
        assert "SECRET" not in raw
        assert "hunter2" not in raw
        assert REDACTED in raw

    def test_a_bound_logger_repeats_its_fields(self, captured):
        logger = get_logger("test").bind(symbol="XAUUSD")
        logger.info("one")
        logger.info("two")

        records = captured()
        assert all(record["metadata"]["symbol"] == "XAUUSD" for record in records)

    def test_binding_can_be_extended(self, captured):
        get_logger("test").bind(a=1).bind(b=2).info("both")

        metadata = captured()[0]["metadata"]
        assert metadata["a"] == 1 and metadata["b"] == 2

    def test_an_exception_is_captured_with_its_traceback(self, captured):
        logger = get_logger("test")
        try:
            raise ValueError("bad input")
        except ValueError:
            logger.exception("operation failed")

        record = captured()[0]
        assert record["level"] == "ERROR"
        assert "ValueError" in record["exception"]

    def test_the_level_filters_records(self, tmp_path):
        path = tmp_path / "warn.log"
        configure_logging(level="WARNING", json_output=True, log_file=path)
        logger = get_logger("test")

        logger.debug("hidden")
        logger.info("hidden too")
        logger.warning("visible")

        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert len(records) == 1
        assert records[0]["message"] == "visible"
        logging.getLogger("ShadBotTrader").handlers.clear()

    def test_every_level_works(self, captured):
        logger = get_logger("test")
        for name in ("debug", "info", "warning", "error", "critical"):
            getattr(logger, name)(f"{name} message")

        levels = [record["level"] for record in captured()]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_an_unknown_level_is_refused(self):
        with pytest.raises(ValueError, match="Unknown log level"):
            configure_logging(level="LOUD")

    def test_configuring_from_a_configuration_object(self, tmp_path):
        config = LayeredConfiguration(
            {
                "environment": "production",
                "logging": {"level": "ERROR", "json": True, "file": str(tmp_path / "a.log")},
            }
        )

        root = configure_from(config)

        assert root.level == logging.ERROR
        logging.getLogger("ShadBotTrader").handlers.clear()

    def test_the_environment_is_recorded_on_each_line(self, captured):
        get_logger("test").info("hello")

        assert captured()[0]["environment"] == "test"


class TestFormatter:
    def test_the_json_formatter_produces_valid_json(self):
        formatter = JsonFormatter(environment="test")
        record = logging.LogRecord(
            "ShadBotTrader.x", logging.INFO, "f.py", 1, "message", None, None
        )

        payload = json.loads(formatter.format(record))

        assert payload["message"] == "message"
        assert payload["level"] == "INFO"

    def test_the_logger_name_is_namespaced(self):
        assert get_logger("trading").name == "ShadBotTrader.trading"
        assert get_logger("ShadBotTrader.ai").name == "ShadBotTrader.ai"

    def test_a_structured_logger_exposes_its_component(self, captured):
        StructuredLogger("ShadBotTrader.x", component="Engine").info("hi")

        assert captured()[0]["component"] == "Engine"
