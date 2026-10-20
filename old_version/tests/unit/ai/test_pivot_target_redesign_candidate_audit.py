"""Phase153A pivot target redesign candidate build/audit helpers."""

from __future__ import annotations

from pathlib import Path

from scripts import run_pivot_target_redesign_candidate_audit as phase153


def test_parse_default_phase153_candidates():
    candidates = phase153.parse_candidates(phase153.DEFAULT_CANDIDATES)

    assert [candidate.candidate_id for candidate in candidates] == ["C1", "C2"]
    assert candidates[0].output_name == "pivot_pattern_sequence_tensor_c1_stable_latest"
    assert candidates[0].lookahead_bars == 24
    assert candidates[0].pivot_move_atr == 0.75
    assert candidates[0].pivot_zone_atr == 0.25
    assert candidates[0].min_direction_edge == 1.0
    assert candidates[1].output_name == "pivot_pattern_sequence_tensor_c2_dense_latest"


def test_build_health_and_stability_commands_use_candidate_paths(tmp_path):
    args = phase153.parse_args(
        [
            "--storage-root",
            str(tmp_path / "datasets"),
            "--output-dir",
            str(tmp_path / "logs"),
            "--candidates",
            "C1:stable:24:0.75:0.25:1.0",
            "--build-max-samples",
            "1000",
            "--audit-max-samples",
            "500",
            "--health-full-scan",
            "0",
        ]
    )
    candidate = phase153.parse_candidates(args.candidates)[0]
    tensor_path, meta_path, flat_path = phase153.output_paths(args, candidate)
    build_dir = Path(args.output_dir) / candidate.slug / "build"
    health_dir = Path(args.output_dir) / candidate.slug / "health"
    stability_dir = Path(args.output_dir) / candidate.slug / "stability"

    build = phase153.build_tensor_command(args, candidate, build_dir)
    health = phase153.health_command(args, tensor_path, meta_path, flat_path, build_dir / "latest.json", health_dir)
    stability = phase153.stability_command(args, candidate, flat_path, meta_path, stability_dir)

    assert build[2] == "scripts/build_pivot_pattern_sequence_tensor.py"
    assert build[build.index("--output-name") + 1] == "pivot_pattern_sequence_tensor_c1_stable_latest"
    assert build[build.index("--lookahead-bars") + 1] == "24"
    assert build[build.index("--pivot-zone-atr") + 1] == "0.25"
    assert build[build.index("--max-samples") + 1] == "1000"
    assert health[2] == "scripts/audit_pivot_pattern_sequence_tensor.py"
    assert health[health.index("--tensor-path") + 1] == str(tensor_path)
    assert health[health.index("--full-scan") + 1] == "0"
    assert stability[2] == "scripts/audit_pivot_label_target_stability.py"
    assert stability[stability.index("--flat-path") + 1] == str(flat_path)
    assert stability[stability.index("--meta-path") + 1] == str(meta_path)
    assert stability[stability.index("--max-samples") + 1] == "500"
    assert stability[stability.index("--sensitivity-lookahead-bars") + 1] == "24"


def test_sign_flip_detects_validation_to_test_payoff_flip():
    assert phase153.sign_flip(-0.03, -0.05, 0.01) == 1
    assert phase153.sign_flip(0.03, 0.05, -0.01) == 1
    assert phase153.sign_flip(0.03, 0.05, 0.01) == 0
