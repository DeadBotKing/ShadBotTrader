"""Save a picture of the model's architecture (Phase 48).

The operator asked to see, at the start of every training run, what the
input matrix looks like and what the network is — as a PNG they can
open.

Keras can draw that with ``plot_model``, but only when graphviz and
pydot are installed, which they usually are not on Windows. A missing
diagram must never stop a training run that would otherwise work, so
this module degrades in two steps:

    plot_model  ->  a real PNG of the layer graph
    fallback    ->  a PNG rendered from the text summary
    last resort ->  a .txt summary, and a message saying why

Whatever happens, the run continues and the operator is told exactly
which of the three they got.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class DiagramResult:
    """Where the diagram went, and how it was produced."""

    path: Optional[Path] = None
    method: str = "none"
    reason: str = ""

    @property
    def saved(self) -> bool:
        return self.path is not None

    def describe(self) -> str:
        if not self.saved:
            return f"model diagram not saved ({self.reason})"
        return f"model diagram saved via {self.method}: {self.path}"


def model_summary_text(model: Any) -> str:
    """The Keras summary as a string."""
    buffer = io.StringIO()
    try:
        model.summary(print_fn=lambda line: buffer.write(line + "\n"))
    except Exception as error:  # pragma: no cover - defensive
        return f"(could not read the model summary: {error})"
    return buffer.getvalue()


def save_model_diagram(model: Any, path: str | Path, title: str = "") -> DiagramResult:
    """Write a PNG of ``model``'s architecture, falling back to text."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # 1) The real thing: Keras' own layer graph.
    try:
        import tensorflow as tf

        tf.keras.utils.plot_model(
            model,
            to_file=str(target),
            show_shapes=True,
            show_layer_names=True,
            expand_nested=True,
            dpi=96,
        )
        if target.exists() and target.stat().st_size > 0:
            return DiagramResult(path=target, method="keras plot_model")
    except Exception as error:
        first_error = f"{type(error).__name__}: {error}"
    else:
        first_error = "plot_model produced no file"

    # 2) Draw the text summary into a PNG so the operator still gets an
    #    image they can open next to the others.
    summary = model_summary_text(model)
    drawn = _summary_to_png(summary, target, title)
    if drawn is not None:
        return DiagramResult(
            path=drawn,
            method="text summary rendered to PNG",
            reason=f"plot_model unavailable ({first_error})",
        )

    # 3) Plain text, clearly labelled.
    text_path = target.with_suffix(".txt")
    text_path.write_text(f"{title}\n\n{summary}" if title else summary, encoding="utf-8")
    return DiagramResult(
        path=text_path,
        method="text file",
        reason=(
            f"no PNG backend available ({first_error}); install graphviz and "
            f"pydot for a real diagram"
        ),
    )


#: Box-drawing characters Keras uses, and their ASCII equivalents.
_BOX_GLYPHS = {
    "─": "-",
    "━": "=",
    "│": "|",
    "┃": "|",
    "┌": "+",
    "┐": "+",
    "└": "+",
    "┘": "+",
    "├": "+",
    "┤": "+",
    "┬": "+",
    "┴": "+",
    "┼": "+",
    "┏": "+",
    "┓": "+",
    "┗": "+",
    "┛": "+",
    "┣": "+",
    "┫": "+",
    "┳": "+",
    "┻": "+",
    "╋": "+",
    "╇": "+",
    "╈": "+",
    "╉": "+",
    "╊": "+",
    "▀": "=",
    "▄": "=",
    "█": "#",
    "■": "*",
    "•": "*",
}


def _to_ascii_box(line: str) -> str:
    """Replace box-drawing glyphs the default font cannot render."""
    return "".join(_BOX_GLYPHS.get(character, character) for character in line)


def _summary_to_png(summary: str, target: Path, title: str) -> Optional[Path]:
    """Render text into a PNG using Pillow, if it is installed."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    lines: List[str] = ([title, ""] if title else []) + summary.splitlines()
    if not lines:
        return None

    # Keras draws its summary with box-drawing characters. The default
    # Pillow bitmap font has no glyphs for them, so they render as empty
    # squares and the table becomes unreadable. ASCII says the same
    # thing and actually renders.
    lines = [_to_ascii_box(line) for line in lines]

    try:
        font = ImageFont.load_default()
        line_height = 14
        width = max(560, min(1600, 8 * max(len(line) for line in lines) + 40))
        height = line_height * len(lines) + 40

        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((20, 20 + index * line_height), line, fill="black", font=font)
        image.save(target)
        return target
    except Exception:
        return None


def describe_input_matrix(
    rows: int,
    columns: int,
    window_size: int,
    horizon: int,
    candle_columns: int = 14,
) -> List[str]:
    """Plain lines describing the matrix a model is about to train on.

    Printed at the start of every run because "what am I actually
    feeding this thing" is the first question, and it used to require
    reading three files to answer.
    """
    windows = max(rows - window_size - horizon + 1, 0)
    catalogue = max(columns - candle_columns, 0)
    return [
        f"dataset matrix : {rows:,} rows x {columns} columns",
        f"                 {candle_columns} candle-derived + {catalogue} catalogue features",
        f"model input    : {window_size} rows x {columns} columns per window",
        f"windows        : {windows:,} (stride 1, horizon {horizon})",
        f"tensor shape   : ({windows:,}, {window_size}, {columns})",
    ]
