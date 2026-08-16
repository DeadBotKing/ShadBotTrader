"""Read, inspect and convert the project's Parquet files.

Parquet is a *binary columnar* format — it is compressed and encoded, so
opening it in Notepad shows nothing but noise. That is by design: it
makes the files small and fast to query. Use this tool (or pandas) to
see the numbers.

    python scripts/parquet_view.py list
    python scripts/parquet_view.py show datasets/raw/XAUUSD_I/5M/v1.parquet
    python scripts/parquet_view.py show <file> --rows 50 --tail
    python scripts/parquet_view.py info <file>
    python scripts/parquet_view.py csv  <file>
    python scripts/parquet_view.py csv  <file> --out prices.csv
    python scripts/parquet_view.py excel <file> --out prices.xlsx
    python scripts/parquet_view.py convert-all --out-dir exported_csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS = REPO_ROOT / "datasets"


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return pd.read_parquet(path)


def _wide_display() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda value: f"{value:,.5f}")


def cmd_list(args: argparse.Namespace) -> int:
    """List every Parquet file in the project with its size and row count."""
    root = Path(args.root)
    files = sorted(root.rglob("*.parquet"))
    if not files:
        print(f"No .parquet files under {root}")
        return 0

    print(f"{len(files)} Parquet file(s) under {root}\n")
    header = f"{'rows':>8} {'cols':>5} {'size':>10}  path"
    print(header)
    print("-" * len(header))

    for path in files[: args.limit]:
        try:
            frame = pd.read_parquet(path)
            rows, cols = frame.shape
        except Exception as error:  # pragma: no cover - unreadable file
            print(f"{'?':>8} {'?':>5} {'?':>10}  {path}  ({error})")
            continue
        size = path.stat().st_size
        print(
            f"{rows:>8} {cols:>5} {size / 1024:>9.1f}K  "
            f"{path.relative_to(root) if path.is_relative_to(root) else path}"
        )

    if len(files) > args.limit:
        print(f"\n... and {len(files) - args.limit} more (use --limit)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print the actual numbers."""
    _wide_display()
    frame = _read(Path(args.path))

    print(f"File   : {args.path}")
    print(f"Shape  : {frame.shape[0]} rows x {frame.shape[1]} columns")
    print(f"Columns: {', '.join(frame.columns)}")
    print()

    if args.columns:
        wanted = [name.strip() for name in args.columns.split(",")]
        missing = [name for name in wanted if name not in frame.columns]
        if missing:
            raise SystemExit(f"Unknown column(s): {', '.join(missing)}")
        frame = frame[wanted]

    view = frame.tail(args.rows) if args.tail else frame.head(args.rows)
    print(view.to_string())

    if len(frame) > args.rows:
        shown = "last" if args.tail else "first"
        print(f"\n({shown} {args.rows} of {len(frame)} rows — use --rows N for more)")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show schema, dtypes and summary statistics."""
    _wide_display()
    path = Path(args.path)
    frame = _read(path)

    print(f"File  : {path}")
    print(f"Size  : {path.stat().st_size / 1024:.1f} KB on disk")
    print(f"Shape : {frame.shape[0]} rows x {frame.shape[1]} columns")
    print()
    print("=== Columns ===")
    for name in frame.columns:
        nulls = frame[name].isna().sum()
        print(f"  {name:<24} {str(frame[name].dtype):<20} nulls={nulls}")

    numeric = frame.select_dtypes("number")
    if not numeric.empty:
        print("\n=== Statistics (numeric columns) ===")
        print(numeric.describe().to_string())
    return 0


def cmd_csv(args: argparse.Namespace) -> int:
    """Convert to CSV — readable in Notepad, Excel or anything else."""
    frame = _read(Path(args.path))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        print(f"Wrote {len(frame)} rows to {out}")
    else:
        frame.to_csv(sys.stdout, index=False)
    return 0


def cmd_excel(args: argparse.Namespace) -> int:
    """Convert to a real .xlsx workbook."""
    frame = _read(Path(args.path))
    out = Path(args.out or Path(args.path).with_suffix(".xlsx").name)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_excel(out, index=False)
    except ImportError:
        raise SystemExit(
            "Writing .xlsx needs openpyxl:  pip install openpyxl\n"
            "Or use the 'csv' command, which Excel opens natively."
        ) from None
    print(f"Wrote {len(frame)} rows to {out}")
    return 0


def cmd_convert_all(args: argparse.Namespace) -> int:
    """Convert every Parquet file under a root into CSV."""
    root = Path(args.root)
    out_dir = Path(args.out_dir)
    files = sorted(root.rglob("*.parquet"))
    if not files:
        print(f"No .parquet files under {root}")
        return 0

    converted = 0
    for path in files:
        relative = path.relative_to(root) if path.is_relative_to(root) else Path(path.name)
        target = out_dir / relative.with_suffix(".csv")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            pd.read_parquet(path).to_csv(target, index=False)
            converted += 1
        except Exception as error:  # pragma: no cover
            print(f"  skipped {relative}: {error}")

    print(f"Converted {converted} file(s) into {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect and convert Parquet files (they are binary, not text).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    listing = subparsers.add_parser("list", help="list all Parquet files")
    listing.add_argument("--root", default=str(DATASETS))
    listing.add_argument("--limit", type=int, default=40)
    listing.set_defaults(func=cmd_list)

    show = subparsers.add_parser("show", help="print the numbers")
    show.add_argument("path")
    show.add_argument("--rows", type=int, default=20)
    show.add_argument("--tail", action="store_true", help="show the end instead")
    show.add_argument("--columns", default=None, help="comma-separated subset")
    show.set_defaults(func=cmd_show)

    info = subparsers.add_parser("info", help="schema and statistics")
    info.add_argument("path")
    info.set_defaults(func=cmd_info)

    csv = subparsers.add_parser("csv", help="convert to CSV")
    csv.add_argument("path")
    csv.add_argument("--out", default=None, help="output file (default: stdout)")
    csv.set_defaults(func=cmd_csv)

    excel = subparsers.add_parser("excel", help="convert to .xlsx")
    excel.add_argument("path")
    excel.add_argument("--out", default=None)
    excel.set_defaults(func=cmd_excel)

    convert = subparsers.add_parser("convert-all", help="convert every file to CSV")
    convert.add_argument("--root", default=str(DATASETS))
    convert.add_argument("--out-dir", default="exported_csv")
    convert.set_defaults(func=cmd_convert_all)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
