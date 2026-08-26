"""Phase 36 — you can watch a training run while it happens.

Regression suite for three defects reported by the operator:

    "when I press Train both models, neither PowerShell nor the web page
     shows me anything about the training — no accuracy, no percentage"

1. The dashboard ran scripts through ``subprocess.run(capture_output=...)``,
   which returns nothing until the process EXITS. A twenty-minute run
   showed a blank page and then, at the end, twenty lines.
2. ``ConsoleProgressReporter`` had existed since Phase 13 and no caller
   ever passed it, so the trainer ran with a NullProgressReporter and
   printed nothing per epoch.
3. The trainer computed accuracy every epoch and kept only ``val_loss``,
   so "is the model any good?" had no answer anywhere in the system.
"""

import threading
import time
from pathlib import Path

import pytest

from ShadBotTrader.presentation.commands.commands import Command, CommandKind, CommandStatus
from ShadBotTrader.presentation.commands.handlers import (
    AccountCommandHandlers,
    read_run_log,
    run_log_path,
)

SLOW_SCRIPT = """
import time
for index in range(6):
    print(f"epoch {index + 1}/6 loss {1.0 / (index + 1):.4f}")
    time.sleep(0.4)
"""

CRASHING_SCRIPT = """
print("epoch 1/2 loss 0.5")
raise SystemExit("model diverged")
"""


@pytest.fixture
def handlers(tmp_path):
    handler = AccountCommandHandlers(tmp_path / "shadbot.db", tmp_path / "datasets")
    handler._run_log_dir = tmp_path / "run_logs"
    return handler


def write(tmp_path: Path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


# ------------------------------------------------- 1) live streaming ----
class TestOutputIsVisibleWhileTheScriptRuns:
    def test_the_log_fills_up_before_the_script_finishes(self, handlers, tmp_path):
        """The whole point: progress DURING the run, not after it."""
        script = write(tmp_path, "slow.py", SLOW_SCRIPT)
        captured: dict = {}

        def run():
            captured["result"] = handlers._run_script(
                Command(CommandKind.TRAIN_DUAL_MODELS, {}),
                [script],
                "done",
                time.monotonic(),
                timeout=60,
            )

        thread = threading.Thread(target=run)
        thread.start()
        try:
            time.sleep(1.3)
            mid_run = read_run_log("train_dual_models", handlers._run_log_dir)
        finally:
            thread.join(timeout=30)

        epochs = [line for line in mid_run if line.startswith("epoch")]
        assert epochs, "the log was empty while the script was still running"
        assert len(epochs) < 6, "the script had already finished; this proves nothing"
        assert captured["result"].status is CommandStatus.SUCCEEDED

    def test_the_command_is_recorded_at_the_top_of_the_log(self, handlers, tmp_path):
        script = write(tmp_path, "quick.py", "print('hello')")
        handlers._run_script(
            Command(CommandKind.TRAIN_DUAL_MODELS, {}), [script], "done", time.monotonic()
        )

        lines = read_run_log("train_dual_models", handlers._run_log_dir)

        assert lines[0].startswith("$ ")
        assert "quick.py" in lines[0]

    def test_a_failure_keeps_the_output_that_led_to_it(self, handlers, tmp_path):
        script = write(tmp_path, "boom.py", CRASHING_SCRIPT)

        result = handlers._run_script(
            Command(CommandKind.TRAIN_DUAL_MODELS, {}), [script], "done", time.monotonic()
        )

        assert result.status is CommandStatus.FAILED
        assert "epoch 1/2" in result.detail
        assert "epoch 1/2" in "\n".join(read_run_log("train_dual_models", handlers._run_log_dir))

    def test_each_command_writes_its_own_log(self, handlers, tmp_path):
        script = write(tmp_path, "quick.py", "print('one')")
        handlers._run_script(
            Command(CommandKind.TRAIN_DUAL_MODELS, {}), [script], "done", time.monotonic()
        )
        handlers._run_script(
            Command(CommandKind.BUILD_DATASET, {}), [script], "done", time.monotonic()
        )

        assert run_log_path("train_dual_models", handlers._run_log_dir).exists()
        assert run_log_path("build_dataset", handlers._run_log_dir).exists()

    def test_a_missing_log_reads_as_empty_not_an_error(self, tmp_path):
        assert read_run_log("never_run", tmp_path / "nowhere") == []

    def test_the_log_name_cannot_escape_its_directory(self, tmp_path):
        """A command value is not a path; treat it as untrusted anyway."""
        path = run_log_path("../../etc/passwd", tmp_path)

        assert path.parent == tmp_path
        assert ".." not in path.name


# ------------------------------------------- 2) the reporter is wired ---
class TestTheProgressReporterIsActuallyUsed:
    def test_the_script_passes_a_console_reporter(self):
        """It existed since Phase 13 and nothing ever passed it."""
        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "ConsoleProgressReporter" in source
        assert "progress=reporter" in source

    def test_quiet_turns_the_per_epoch_log_off(self):
        import importlib.util

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.parse_args(["--quiet"]).quiet is True
        assert module.parse_args([]).quiet is False

    def test_the_reporter_reports_every_epoch(self):
        import io

        from ShadBotTrader.infrastructure.ai.training_progress import (
            ConsoleProgressReporter,
            EpochMetrics,
            FoldInfo,
            TrainingPlanInfo,
        )

        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        plan = TrainingPlanInfo(
            model_id="signal",
            model_version=1,
            total_folds=2,
            epochs_per_fold=2,
            learning_rate=1.5e-4,
            batch_size=8,
            window_size=500,
            n_features=123,
            total_samples=900,
            seed=42,
        )
        fold = FoldInfo(
            fold_index=0,
            total_folds=2,
            train_samples=800,
            val_samples=4,
            train_start=0,
            train_end=800,
            val_start=800,
            val_end=804,
        )

        reporter.on_train_begin(plan)
        reporter.on_fold_begin(fold)
        reporter.on_epoch_end(
            fold,
            EpochMetrics(
                epoch=0, total_epochs=2, loss=0.75, val_loss=0.29, accuracy=0.88, val_accuracy=1.0
            ),
        )
        reporter.on_fold_end(fold, 0.29)
        reporter.on_train_end([0.29])

        output = stream.getvalue()
        assert "epoch   1/2" in output
        assert "acc=0.8800" in output
        assert "val_acc=1.0000" in output
        assert "OK fold" in output  # fold completion marker
        assert "eta" in output


# ------------------------------------------------ 3) quality metrics ----
class TestTrainingQualityIsReported:
    def test_the_trainer_keeps_more_than_the_loss(self):
        """fold_metrics is what makes 'is it any good?' answerable."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        trainer = WavenetTrainer(series=[[0.0, 0.0]], target_column=1, window_size=2)

        assert hasattr(trainer, "fold_metrics")
        assert trainer.fold_metrics == []

    def test_the_service_surfaces_the_metrics(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "ShadBotTrader"
            / "application"
            / "services"
            / "dual_model_service.py"
        ).read_text(encoding="utf-8")

        assert '"fold_metrics"' in source

    def test_accuracy_is_compared_against_the_majority_baseline(self, capsys):
        """70% accuracy on a 70/15/15 split means the model learned nothing."""
        import importlib.util

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Role:
            name = "signal"

        module.print_quality(
            {
                "fold_metrics": [{"val_accuracy": 0.70, "val_loss": 0.4}],
                "dataset": {"label_distribution": {"SELL": 15, "HOLD": 70, "BUY": 15}},
            },
            Role(),
        )

        printed = capsys.readouterr().out
        assert "70.0%" in printed
        assert "NO BETTER than" in printed

    def test_beating_the_baseline_is_stated_plainly(self, capsys):
        import importlib.util

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Role:
            name = "signal"

        module.print_quality(
            {
                "fold_metrics": [{"val_accuracy": 0.91, "val_loss": 0.2}],
                "dataset": {"label_distribution": {"SELL": 30, "HOLD": 40, "BUY": 30}},
            },
            Role(),
        )

        printed = capsys.readouterr().out
        assert "BETTER than" in printed
        assert "NO BETTER than" not in printed

    def test_the_range_model_reports_its_error_in_money(self, capsys):
        import importlib.util

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Role:
            name = "range"

        module.print_quality({"fold_metrics": [{"val_mae": 0.001, "val_loss": 0.0002}]}, Role())

        printed = capsys.readouterr().out
        assert "val_mae" in printed
        assert "USD" in printed

    def test_no_metrics_prints_nothing_rather_than_guessing(self, capsys):
        import importlib.util

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Role:
            name = "signal"

        module.print_quality({"fold_metrics": []}, Role())

        assert capsys.readouterr().out == ""


# ------------------------------------- 4) the dashboard's storage root --
class TestScriptButtonsRespectTheStorageRoot:
    """A bug found while verifying Phase 36 live.

    The dashboard accepts ``--storage-root`` and every handler that talks
    to the store directly honoured it — but the four buttons that shell
    out to a script never passed it on, so those scripts silently used
    the repository default. Training "XAUUSD" reported "no stored
    candles" while the dashboard's own /data page listed thousands.
    """

    SCRIPT_COMMANDS = [
        (CommandKind.BUILD_DATASET, "run_training_dataset.py"),
        (CommandKind.WEEKLY_UPDATE, "run_weekly_update.py"),
        (CommandKind.TRAIN_DUAL_MODELS, "run_dual_models.py"),
        (CommandKind.RUN_LIVE_TICK, "run_live_loop.py"),
    ]

    @pytest.mark.parametrize("kind,script", SCRIPT_COMMANDS)
    def test_the_storage_root_reaches_the_script(self, tmp_path, monkeypatch, kind, script):
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path / "my-datasets")
        handlers._run_log_dir = tmp_path / "run_logs"
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            captured["arguments"] = list(arguments)
            from ShadBotTrader.presentation.commands.commands import CommandResult

            return CommandResult.success(command.kind, "ok", [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        monkeypatch.setattr(handlers, "missing_timeframes", lambda symbol: [])

        handler = {
            CommandKind.BUILD_DATASET: handlers.build_dataset,
            CommandKind.WEEKLY_UPDATE: handlers.weekly_update,
            CommandKind.TRAIN_DUAL_MODELS: handlers.train_dual_models,
            CommandKind.RUN_LIVE_TICK: handlers.run_live_tick,
        }[kind]

        handler(Command(kind, {"symbol": "XAUUSD"}))

        arguments = captured.get("arguments")
        if arguments is None and kind is CommandKind.TRAIN_DUAL_MODELS:
            pytest.skip("TensorFlow is not installed, so the handler stops earlier")
        assert arguments is not None, "the handler never invoked a script"
        assert script in arguments[0]
        assert "--storage-root" in arguments, f"{script} was run against the default root"
        root = arguments[arguments.index("--storage-root") + 1]
        assert root.endswith("my-datasets")

    @pytest.mark.parametrize("script", [item[1] for item in SCRIPT_COMMANDS])
    def test_every_such_script_accepts_the_flag(self, script):
        """The handler may only pass a flag the script actually parses."""
        source = (Path(__file__).resolve().parents[2] / "scripts" / script).read_text(
            encoding="utf-8"
        )

        assert "--storage-root" in source
