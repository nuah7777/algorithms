"""Measure separate-chaining search costs at different load factors."""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hash_table import HashTable

TABLE_SIZE = 4093
SAMPLE_SIZE = 1000
RANDOM_SEED = 20261120
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIRECTORY / "results.csv"
SVG_PATH = OUTPUT_DIRECTORY / "results.svg"
CSV_HEADER = (
    "target_load",
    "actual_load",
    "buckets",
    "items",
    "success_samples",
    "success_measured",
    "success_theory",
    "failure_samples",
    "failure_measured",
    "failure_theory",
)


def _count_comparisons(table: HashTable, key: str) -> int:
    bucket_index, _ = table.hash_details(key)
    node = table._buckets[bucket_index]
    comparisons = 0
    while node is not None:
        comparisons += 1
        if node.key == key:
            return comparisons
        node = node.next
    return comparisons


def _make_url(rng: random.Random, index: int) -> str:
    host = f"{rng.getrandbits(64):016x}"
    path = f"{rng.getrandbits(32):08x}/{index}"
    return f"https://{host}.example/{path}"


def _measure_load_factor(
    target_load: float, rng: random.Random
) -> tuple[float, ...]:
    item_count = round(target_load * TABLE_SIZE)
    table = HashTable(TABLE_SIZE, max_load=None)
    urls = []
    for index in range(item_count):
        url = _make_url(rng, index)
        urls.append(url)
        table.insert(url, index)
    if table.capacity != TABLE_SIZE:
        raise RuntimeError("the experiment hash table changed its fixed capacity")

    sample_count = min(SAMPLE_SIZE, item_count)
    successful_total = 0
    for _ in range(sample_count):
        successful_total += _count_comparisons(table, rng.choice(urls))
    successful_average = successful_total / sample_count

    failed_total = 0
    for index in range(SAMPLE_SIZE):
        missing_url = f"https://missing-{rng.getrandbits(64):016x}.invalid/{index}"
        failed_total += _count_comparisons(table, missing_url)
    failed_average = failed_total / SAMPLE_SIZE

    actual_load = len(table) / table.capacity
    return (
        target_load,
        actual_load,
        table.capacity,
        item_count,
        sample_count,
        successful_average,
        1 + actual_load / 2,
        SAMPLE_SIZE,
        failed_average,
        actual_load,
    )


def _write_csv(rows: list[tuple[float, ...]]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(
                (
                    f"{row[0]:.2f}",
                    f"{row[1]:.4f}",
                    row[2],
                    row[3],
                    row[4],
                    f"{row[5]:.4f}",
                    f"{row[6]:.4f}",
                    row[7],
                    f"{row[8]:.4f}",
                    f"{row[9]:.4f}",
                )
            )


def _write_svg(rows: list[tuple[float, ...]]) -> None:
    width, height = 960, 560
    left, right, top, bottom = 82, 30, 70, 72
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_max, y_max = 4.0, 5.0

    def point(load: float, value: float) -> tuple[float, float]:
        x = left + load / x_max * plot_width
        y = top + (y_max - value) / y_max * plot_height
        return x, y

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Arial,sans-serif;fill:#222}"
        ".grid{stroke:#ddd;stroke-width:1}.axis{stroke:#333;stroke-width:1.5}"
        ".success{stroke:#1769aa;fill:none}.failure{stroke:#d35400;fill:none}"
        ".theory{stroke-dasharray:7 5;stroke-width:2}.measured{stroke-width:2.5}"
        "</style>",
        '<text x="480" y="32" text-anchor="middle" font-size="20">'
        "Separate-chaining search cost by load factor</text>",
    ]

    for value in range(6):
        y = point(0, value)[1]
        elements.append(
            f'<line class="grid" x1="{left}" y1="{y:.1f}" '
            f'x2="{width - right}" y2="{y:.1f}"/>'
        )
        elements.append(
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end">'
            f"{value}</text>"
        )
    for value in range(5):
        x = point(value, 0)[0]
        elements.append(
            f'<line class="grid" x1="{x:.1f}" y1="{top}" '
            f'x2="{x:.1f}" y2="{height - bottom}"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{height - bottom + 24}" '
            f'text-anchor="middle">{value}</text>'
        )

    elements.extend(
        (
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{height - bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{height - bottom}" '
            f'x2="{width - right}" y2="{height - bottom}"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" '
            'text-anchor="middle">Load factor (α)</text>',
            f'<text x="22" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 22 {top + plot_height / 2})" '
            'text-anchor="middle">Average nodes compared</text>',
        )
    )

    series = (
        ("Success measured", 5, "success measured"),
        ("Success theory: 1 + α/2", 6, "success theory"),
        ("Failure measured", 8, "failure measured"),
        ("Failure theory: α", 9, "failure theory"),
    )
    legend_y = 50
    for series_index, (label, column, style) in enumerate(series):
        group, line_style = style.split()
        coordinates = [point(row[1], row[column]) for row in rows]
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)
        elements.append(
            f'<polyline class="{group} {line_style}" points="{points}"/>'
        )
        legend_x = 95 + series_index * 205
        elements.append(
            f'<line class="{group} {line_style}" x1="{legend_x}" '
            f'y1="{legend_y}" x2="{legend_x + 28}" y2="{legend_y}"/>'
        )
        elements.append(
            f'<text x="{legend_x + 34}" y="{legend_y + 5}" font-size="12">'
            f"{escape(label)}</text>"
        )

    elements.append("</svg>")
    SVG_PATH.write_text("\n".join(elements) + "\n", encoding="utf-8")


def _print_table(rows: list[tuple[float, ...]]) -> None:
    print(
        "target α | actual α | success measured/theory | "
        "failure measured/theory"
    )
    for row in rows:
        print(
            f"{row[0]:7.2f} | {row[1]:8.4f} | "
            f"{row[5]:8.4f} / {row[6]:8.4f} | "
            f"{row[8]:8.4f} / {row[9]:8.4f}"
        )


def run_experiment() -> list[tuple[float, ...]]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    rng = random.Random(RANDOM_SEED)
    rows = [_measure_load_factor(load, rng) for load in LOAD_FACTORS]
    _write_csv(rows)
    _write_svg(rows)
    _print_table(rows)
    return rows


if __name__ == "__main__":
    run_experiment()
