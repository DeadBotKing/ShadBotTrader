#!/usr/bin/env python3
"""Inspect stored datasets and the real feature catalog in a local page.

    python scripts/inspect_dataset_features.py --storage-root datasets --port 8765

Open http://127.0.0.1:8765
The page reads Parquet candles from the Data Platform and computes
FXTradingFeatureSetV1 with the same calculators the range model uses.
It does not train, and it does not write datasets.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.domain.feature.ports import FeatureInputContext  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.infrastructure.data.parquet_candle_store import (  # noqa: E402
    ParquetCandleStore,
    _parse_iso,
)
from ShadBotTrader.infrastructure.feature.calculator_registry import (  # noqa: E402
    CalculatorRegistry,
)
from ShadBotTrader.infrastructure.feature.standard_catalog import (  # noqa: E402
    standard_feature_set,
)

PAGE_PATH = Path(__file__).with_name("dataset_feature_inspector.html")
_VERSION_RE_NAME = "v"
_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str, int, str], dict[str, Any]] = {}
_JOBS: dict[tuple[str, str, int, str], dict[str, Any]] = {}
_STORE_ROOT = REPO_ROOT / "datasets"


def _json_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def list_datasets(root: Path) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for layer in ("processed", "raw"):
        base = root / layer
        if not base.is_dir():
            continue
        for symbol_dir in sorted(path for path in base.iterdir() if path.is_dir()):
            for timeframe_dir in sorted(path for path in symbol_dir.iterdir() if path.is_dir()):
                for path in sorted(timeframe_dir.glob("v*.parquet")):
                    stem = path.stem
                    if not stem.startswith(_VERSION_RE_NAME) or not stem[1:].isdigit():
                        continue
                    found.append(
                        {
                            "symbol": symbol_dir.name,
                            "timeframe": timeframe_dir.name,
                            "version": int(stem[1:]),
                            "layer": layer,
                            "bytes": path.stat().st_size,
                            "path": str(path.relative_to(root)),
                        }
                    )
    return found


def _dataset_path(root: Path, symbol: str, timeframe: str, version: int, layer: str) -> Path:
    if layer not in ("processed", "raw"):
        raise ValueError(f"unknown layer {layer!r}")
    symbol_label = symbol.strip().upper().replace("/", "").replace("\\", "").replace("-", "")
    timeframe_label = timeframe.strip().upper()
    Timeframe(timeframe_label)
    path = root / layer / symbol_label / timeframe_label / f"v{version}.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"dataset not found: {path}")
    return path


def read_candles(path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    rows: list[dict[str, Any]] = []
    for row in table.to_pylist():
        opened = _parse_iso(row.get("open_time"))
        if opened is None:
            continue
        rows.append(
            {
                "time": opened.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0.0),
            }
        )
    rows.sort(key=lambda item: item["time"])
    return rows


def feature_catalog() -> list[dict[str, Any]]:
    catalog = []
    for definition in standard_feature_set().definitions:
        catalog.append(
            {
                "id": definition.feature_id.value,
                "name": definition.name,
                "family": definition.family,
                "type": definition.feature_type.value,
                "causality": definition.causality.value,
                "scope": definition.model_scope.value,
                "lookback": int(definition.lookback),
                "leakage": definition.leakage_reason or "",
                "description": definition.description,
            }
        )
    return catalog


def _job_key(symbol: str, timeframe: str, version: int, layer: str) -> tuple[str, str, int, str]:
    return (symbol.strip().upper(), timeframe.strip().upper(), int(version), layer)


def compute_dataset(root: Path, symbol: str, timeframe: str, version: int, layer: str) -> dict[str, Any]:
    key = _job_key(symbol, timeframe, version, layer)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        job = _JOBS.get(key)
        if job is None or job.get("status") == "failed":
            job = {"status": "running", "done": 0, "total": 0, "error": ""}
            _JOBS[key] = job
            threading.Thread(
                target=_compute_worker,
                args=(root, key),
                daemon=True,
            ).start()
    return {"status": job["status"], "done": job["done"], "total": job["total"], "error": job["error"]}


def _compute_worker(root: Path, key: tuple[str, str, int, str]) -> None:
    symbol, timeframe, version, layer = key
    job = _JOBS[key]
    try:
        path = _dataset_path(root, symbol, timeframe, version, layer)
        candles = read_candles(path)
        if not candles:
            raise ValueError("dataset has no readable candles")
        from ShadBotTrader.domain.market.candle import Candle
        from ShadBotTrader.domain.market.price import Price
        from ShadBotTrader.domain.market.timestamp import Timestamp

        domain_candles = [
            Candle(
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(_parse_iso(row["time"])),
                open_price=Price(str(row["open"])),
                high=Price(str(row["high"])),
                low=Price(str(row["low"])),
                close=Price(str(row["close"])),
                volume=row["volume"],
            )
            for row in candles
        ]
        definitions = list(standard_feature_set().definitions)
        job["total"] = len(definitions)
        context = FeatureInputContext(
            symbol=Symbol(symbol),
            timeframe=Timeframe(timeframe),
            candles=domain_candles,
        )
        registry = CalculatorRegistry()
        width = len(candles)
        values: dict[str, list[float | None]] = {}
        errors: dict[str, str] = {}
        for index, definition in enumerate(definitions, start=1):
            feature_id = definition.feature_id.value
            calculator = registry.resolve(definition.calculator_family)
            if calculator is None:
                errors[feature_id] = "no calculator"
                values[feature_id] = [None] * width
            else:
                try:
                    result = calculator.compute(definition, context)
                    column = [_json_number(point.value) for point in result.points]
                    if len(column) != width:
                        errors[feature_id] = f"length {len(column)} != {width}"
                        column = (column + [None] * width)[:width]
                    values[feature_id] = column
                except Exception as error:  # one feature must not hide the dataset
                    errors[feature_id] = f"{type(error).__name__}: {error}"
                    values[feature_id] = [None] * width
            job["done"] = index
        payload = {
            "status": "ready",
            "symbol": symbol,
            "timeframe": timeframe,
            "version": version,
            "layer": layer,
            "rows": width,
            "candles": candles,
            "features": feature_catalog(),
            "values": values,
            "errors": errors,
            "review": _review(candles, feature_catalog(), values, errors),
        }
        with _LOCK:
            _CACHE[key] = payload
            job["status"] = "ready"
    except Exception as error:
        job["status"] = "failed"
        job["error"] = f"{type(error).__name__}: {error}"
        traceback.print_exc()


def _review(
    candles: list[dict[str, Any]],
    features: list[dict[str, Any]],
    values: dict[str, list[float | None]],
    errors: dict[str, str],
) -> dict[str, Any]:
    rows = len(candles)
    constant = []
    tail_null = []
    high_null = []
    divergence_hits = []
    for feature in features:
        column = values.get(feature["id"], [])
        present = [value for value in column if value is not None]
        null_rate = 1.0 - (len(present) / rows if rows else 0.0)
        if null_rate >= 0.5:
            high_null.append({"id": feature["id"], "null_rate": round(null_rate, 4), "family": feature["family"]})
        if column and column[-1] is None and any(value is not None for value in column):
            tail_null.append(feature["id"])
        if len(present) >= 20:
            rounded = {round(value, 8) for value in present}
            if len(rounded) <= 1:
                constant.append(feature["id"])
        if feature["family"] == "divergence":
            hits = sum(1 for value in present if value >= 0.5)
            divergence_hits.append({"id": feature["id"], "hits": hits, "rows": rows, "leakage": feature["leakage"]})
    return {
        "rows": rows,
        "feature_count": len(features),
        "causal": sum(1 for feature in features if feature["causality"] == "causal"),
        "non_causal": sum(1 for feature in features if feature["causality"] != "causal"),
        "range_only": sum(1 for feature in features if feature["scope"] == "range"),
        "signal_only": sum(1 for feature in features if feature["scope"] == "signal"),
        "compute_errors": errors,
        "constant_features": constant,
        "tail_null_features": tail_null,
        "high_null_features": high_null[:30],
        "divergence_hits": divergence_hits,
        "volume_zero_rate": (
            sum(1 for row in candles if row["volume"] == 0.0) / rows if rows else 0.0
        ),
    }


def job_status(symbol: str, timeframe: str, version: int, layer: str) -> dict[str, Any]:
    key = _job_key(symbol, timeframe, version, layer)
    with _LOCK:
        if key in _CACHE:
            item = _CACHE[key]
            return {
                "status": "ready",
                "rows": item["rows"],
                "done": len(item["features"]),
                "total": len(item["features"]),
            }
        job = _JOBS.get(key)
    if job is None:
        return {"status": "idle", "done": 0, "total": 0}
    return {"status": job["status"], "done": job["done"], "total": job["total"], "error": job.get("error", "")}


def candle_payload(symbol: str, timeframe: str, version: int, layer: str, index: int) -> dict[str, Any]:
    key = _job_key(symbol, timeframe, version, layer)
    with _LOCK:
        item = _CACHE.get(key)
    if item is None:
        raise LookupError("features are not ready")
    if index < 0 or index >= item["rows"]:
        raise IndexError(f"candle index {index} outside 0..{item['rows'] - 1}")
    candle = item["candles"][index]
    features = []
    for feature in item["features"]:
        column = item["values"].get(feature["id"], [])
        features.append({**feature, "value": column[index] if index < len(column) else None})
    return {"index": index, "candle": candle, "features": features, "review": item["review"]}


class Handler(BaseHTTPRequestHandler):
    server_version = "DatasetFeatureInspector/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[inspector] {self.address_string()} {fmt % args}", flush=True)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path in ("/", "/index.html"):
                self._send(200, PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/datasets":
                self._json(200, {"datasets": list_datasets(_STORE_ROOT)})
                return
            if parsed.path == "/api/prepare":
                symbol, timeframe, version, layer = _query_identity(query)
                state = compute_dataset(_STORE_ROOT, symbol, timeframe, version, layer)
                if state.get("status") == "ready" or _job_key(symbol, timeframe, version, layer) in _CACHE:
                    key = _job_key(symbol, timeframe, version, layer)
                    item = _CACHE[key]
                    self._json(
                        200,
                        {
                            "status": "ready",
                            "symbol": item["symbol"],
                            "timeframe": item["timeframe"],
                            "version": item["version"],
                            "layer": item["layer"],
                            "rows": item["rows"],
                            "candles": item["candles"],
                            "features": item["features"],
                            "review": item["review"],
                        },
                    )
                    return
                self._json(200, state)
                return
            if parsed.path == "/api/status":
                symbol, timeframe, version, layer = _query_identity(query)
                self._json(200, job_status(symbol, timeframe, version, layer))
                return
            if parsed.path == "/api/candle":
                symbol, timeframe, version, layer = _query_identity(query)
                index = int(query.get("index", ["-1"])[0])
                self._json(200, candle_payload(symbol, timeframe, version, layer, index))
                return
            self._json(404, {"error": "not found"})
        except (FileNotFoundError, ValueError, LookupError, IndexError) as error:
            self._json(400, {"error": str(error)})
        except Exception as error:
            traceback.print_exc()
            self._json(500, {"error": f"{type(error).__name__}: {error}"})


def _query_identity(query: dict[str, list[str]]) -> tuple[str, str, int, str]:
    symbol = query.get("symbol", [""])[0]
    timeframe = query.get("timeframe", [""])[0]
    version_text = query.get("version", [""])[0]
    layer = query.get("layer", ["processed"])[0] or "processed"
    if not symbol or not timeframe or not version_text:
        raise ValueError("symbol, timeframe, and version are required")
    return symbol, timeframe, int(version_text), layer


def main(argv: list[str] | None = None) -> int:
    global _STORE_ROOT
    parser = argparse.ArgumentParser(description="Open the dataset and feature inspector.")
    parser.add_argument("--storage-root", default="datasets")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    _STORE_ROOT = Path(args.storage_root)
    if not _STORE_ROOT.is_absolute():
        _STORE_ROOT = REPO_ROOT / _STORE_ROOT
    if not PAGE_PATH.is_file():
        raise SystemExit(f"missing page: {PAGE_PATH}")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[inspector] storage={_STORE_ROOT}", flush=True)
    print(f"[inspector] open http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[inspector] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
