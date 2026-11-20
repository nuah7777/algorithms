"""Compare separate chaining and linear probing across load factors."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable

CAPACITY = 4093
SAMPLE_SIZE = 1000
DATA_SEED = 8026
QUERY_SEED = 1802
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIRECTORY / "strategy_comparison.csv"
SVG_PATH = OUTPUT_DIRECTORY / "strategy_comparison.svg"
PDF_PATH = OUTPUT_DIRECTORY / "strategy_comparison_report.pdf"
CSV_HEADER = (
    "target_load",
    "actual_load",
    "capacity",
    "items",
    "samples_per_operation",
    "chaining_success_measured",
    "chaining_success_theory",
    "chaining_failure_measured",
    "chaining_failure_theory",
    "linear_success_measured",
    "linear_success_theory",
    "linear_failure_measured",
    "linear_failure_theory",
)


@dataclass(frozen=True)
class ComparisonRow:
    target_load: float
    actual_load: float
    capacity: int
    items: int
    samples_per_operation: int
    chaining_success_measured: float
    chaining_success_theory: float
    chaining_failure_measured: float
    chaining_failure_theory: float
    linear_success_measured: float
    linear_success_theory: float
    linear_failure_measured: float
    linear_failure_theory: float


def _make_url(rng: random.Random, index: int) -> str:
    host = f"{rng.getrandbits(64):016x}"
    path = f"{rng.getrandbits(32):08x}/{index}"
    return f"https://{host}.example/{path}"


def _measure_load_factor(
    target_load: float,
    urls: list[str],
    query_rng: random.Random,
) -> ComparisonRow:
    item_count = round(target_load * CAPACITY)
    keys = urls[:item_count]
    chaining = HashTable(CAPACITY, max_load=None)
    linear = LinearProbingHashTable(CAPACITY, max_load=None)
    for key in keys:
        chaining.insert(key, key)
        linear.insert(key, key)

    if chaining.capacity != CAPACITY or linear.capacity != CAPACITY:
        raise RuntimeError("comparison tables must keep the same fixed capacity")

    sample_count = min(SAMPLE_SIZE, item_count)
    successful_queries = [
        query_rng.choice(keys) for _ in range(sample_count)
    ]
    failed_queries = [
        f"https://missing-{query_rng.getrandbits(64):016x}.invalid/{index}"
        for index in range(SAMPLE_SIZE)
    ]

    chaining_success = sum(
        chaining.search_cost(key) for key in successful_queries
    ) / sample_count
    chaining_failure = sum(
        chaining.search_cost(key) for key in failed_queries
    ) / SAMPLE_SIZE
    linear_success = sum(
        linear.search_cost(key) for key in successful_queries
    ) / sample_count
    linear_failure = sum(
        linear.search_cost(key) for key in failed_queries
    ) / SAMPLE_SIZE

    actual_load = item_count / CAPACITY
    return ComparisonRow(
        target_load=target_load,
        actual_load=actual_load,
        capacity=CAPACITY,
        items=item_count,
        samples_per_operation=SAMPLE_SIZE,
        chaining_success_measured=chaining_success,
        chaining_success_theory=1 + actual_load / 2,
        chaining_failure_measured=chaining_failure,
        chaining_failure_theory=actual_load,
        linear_success_measured=linear_success,
        linear_success_theory=0.5 * (1 + 1 / (1 - actual_load)),
        linear_failure_measured=linear_failure,
        linear_failure_theory=0.5 * (1 + 1 / (1 - actual_load) ** 2),
    )


def _write_csv(rows: list[ComparisonRow]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(
                (
                    f"{row.target_load:.1f}",
                    f"{row.actual_load:.4f}",
                    row.capacity,
                    row.items,
                    row.samples_per_operation,
                    f"{row.chaining_success_measured:.4f}",
                    f"{row.chaining_success_theory:.4f}",
                    f"{row.chaining_failure_measured:.4f}",
                    f"{row.chaining_failure_theory:.4f}",
                    f"{row.linear_success_measured:.4f}",
                    f"{row.linear_success_theory:.4f}",
                    f"{row.linear_failure_measured:.4f}",
                    f"{row.linear_failure_theory:.4f}",
                )
            )


def _write_svg(rows: list[ComparisonRow]) -> None:
    width, height = 1200, 720
    left, right, top, bottom = 90, 40, 125, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    y_max = 55.0

    def point(load: float, cost: float) -> tuple[float, float]:
        x = left + load * plot_width
        y = top + (y_max - cost) / y_max * plot_height
        return x, y

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Arial,sans-serif;fill:#222}"
        ".grid{stroke:#ddd;stroke-width:1}.axis{stroke:#333;stroke-width:1.5}"
        ".theory{stroke-dasharray:7 5}.series{fill:none;stroke-width:2.5}"
        "</style>",
        '<text x="600" y="32" text-anchor="middle" font-size="21">'
        "Search Cost: Separate Chaining vs Linear Probing</text>",
    ]

    for cost in range(0, 51, 10):
        x1, y = point(0, cost)
        x2, _ = point(1, cost)
        elements.append(
            f'<line class="grid" x1="{x1:.1f}" y1="{y:.1f}" '
            f'x2="{x2:.1f}" y2="{y:.1f}"/>'
        )
        elements.append(
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end">'
            f"{cost}</text>"
        )
    for load_step in range(0, 11, 2):
        load = load_step / 10
        x, y1 = point(load, 0)
        _, y2 = point(load, y_max)
        elements.append(
            f'<line class="grid" x1="{x:.1f}" y1="{y1:.1f}" '
            f'x2="{x:.1f}" y2="{y2:.1f}"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{height - bottom + 24}" '
            f'text-anchor="middle">{load:.1f}</text>'
        )

    elements.extend(
        (
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{height - bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{height - bottom}" '
            f'x2="{width - right}" y2="{height - bottom}"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 22}" '
            'text-anchor="middle">Load factor (alpha)</text>',
            f'<text x="24" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 24 {top + plot_height / 2})" '
            'text-anchor="middle">Average nodes / slots examined</text>',
        )
    )

    series = (
        ("Chaining success", "#1769aa", "chaining_success_measured", "chaining_success_theory"),
        ("Chaining failure", "#00897b", "chaining_failure_measured", "chaining_failure_theory"),
        ("Linear success", "#8e44ad", "linear_success_measured", "linear_success_theory"),
        ("Linear failure", "#d35400", "linear_failure_measured", "linear_failure_theory"),
    )
    for index, (label, color, measured_name, theory_name) in enumerate(series):
        measured_points = [
            point(row.actual_load, getattr(row, measured_name)) for row in rows
        ]
        theory_points = [
            point(row.actual_load, getattr(row, theory_name)) for row in rows
        ]
        for points, class_name in (
            (measured_points, "series"),
            (theory_points, "series theory"),
        ):
            coordinates = " ".join(
                f"{x:.1f},{y:.1f}" for x, y in points
            )
            elements.append(
                f'<polyline class="{class_name}" stroke="{color}" '
                f'points="{coordinates}"/>'
            )

        legend_x = 110 + (index % 2) * 545
        legend_y = 58 + (index // 2) * 24
        elements.append(
            f'<line x1="{legend_x}" y1="{legend_y}" '
            f'x2="{legend_x + 24}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2.5"/>'
        )
        elements.append(
            f'<line x1="{legend_x + 28}" y1="{legend_y}" '
            f'x2="{legend_x + 52}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2.5" stroke-dasharray="7 5"/>'
        )
        elements.append(
            f'<text x="{legend_x + 60}" y="{legend_y + 5}" font-size="13">'
            f"{escape(label)} (measured / theory)</text>"
        )

    elements.append("</svg>")
    SVG_PATH.write_text("\n".join(elements) + "\n", encoding="utf-8")


def _pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_page(title: str, lines: list[str]) -> bytes:
    commands = [
        "BT",
        "/F1 16 Tf",
        "50 800 Td",
        f"({_pdf_literal(title)}) Tj",
        "/F1 8 Tf",
        "11 TL",
        "0 -26 Td",
    ]
    for line in lines:
        commands.append(f"({_pdf_literal(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _write_pdf(rows: list[ComparisonRow]) -> None:
    table_lines = [
        "alpha | Chain S m/t | Chain U m/t | Linear S m/t | Linear U m/t"
    ]
    for row in rows:
        table_lines.append(
            f"{row.actual_load:.1f} | "
            f"{row.chaining_success_measured:.2f}/{row.chaining_success_theory:.2f} | "
            f"{row.chaining_failure_measured:.2f}/{row.chaining_failure_theory:.2f} | "
            f"{row.linear_success_measured:.2f}/{row.linear_success_theory:.2f} | "
            f"{row.linear_failure_measured:.2f}/{row.linear_failure_theory:.2f}"
        )

    largest_deviations = (
        (
            "Chaining success",
            max(
                rows,
                key=lambda row: abs(
                    row.chaining_success_measured - row.chaining_success_theory
                ),
            ),
            "chaining_success_measured",
            "chaining_success_theory",
        ),
        (
            "Chaining failure",
            max(
                rows,
                key=lambda row: abs(
                    row.chaining_failure_measured - row.chaining_failure_theory
                ),
            ),
            "chaining_failure_measured",
            "chaining_failure_theory",
        ),
        (
            "Linear success",
            max(
                rows,
                key=lambda row: abs(
                    row.linear_success_measured - row.linear_success_theory
                ),
            ),
            "linear_success_measured",
            "linear_success_theory",
        ),
        (
            "Linear failure",
            max(
                rows,
                key=lambda row: abs(
                    row.linear_failure_measured - row.linear_failure_theory
                ),
            ),
            "linear_failure_measured",
            "linear_failure_theory",
        ),
    )
    deviation_lines = [
        f"{name}: alpha={row.actual_load:.1f}, "
        f"measured={getattr(row, measured):.2f}, "
        f"theory={getattr(row, theory):.2f}"
        for name, row, measured, theory in largest_deviations
    ]
    high_load = rows[-1]

    first_page = [
        "Capacity: 4093 slots; load factors 0.1 through 0.9.",
        "Both tables use the same deterministic random URLs and insertion order.",
        "Each load factor uses 1000 successful and 1000 unsuccessful queries.",
        "Chaining counts stored nodes visited; probing counts slots checked,",
        "including the terminating empty slot for an unsuccessful probe.",
        "Theory: chaining S=1+alpha/2, U=alpha.",
        "Linear probing S=0.5*(1+1/(1-alpha)),",
        "U=0.5*(1+1/(1-alpha)^2). S=success; U=unsuccessful.",
        "Measured/theory values:",
        *table_lines,
    ]
    second_page = [
        "Findings and interpretation",
        f"At alpha={high_load.actual_load:.1f}, chaining success was "
        f"{high_load.chaining_success_measured:.2f} nodes, versus "
        f"{high_load.chaining_success_theory:.2f} expected.",
        f"At the same load, linear-probing failure was "
        f"{high_load.linear_failure_measured:.2f} slots, versus "
        f"{high_load.linear_failure_theory:.2f} expected.",
        "The linear-probing unsuccessful-search estimate rises sharply near",
        "full occupancy; its alpha=0.9 estimate is about 50.5 probes.",
        "Chaining costs increase more gradually because added entries extend",
        "bucket lists rather than creating long contiguous clusters.",
        "Largest measured/theory deviations in the sampled runs:",
        *deviation_lines,
        "Small differences are expected from finite random samples and the",
        "Horner-hash distribution; both structures show the predicted trend.",
        "Artifacts: strategy_comparison.csv and strategy_comparison.svg.",
    ]

    page_one = _pdf_page("Hash Table Search Cost Comparison", first_page)
    page_two = _pdf_page("Results and Interpretation", second_page)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>"
        ),
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        _pdf_stream(page_one),
        _pdf_stream(page_two),
    ]
    _write_pdf_objects(PDF_PATH, objects)


def _pdf_stream(content: bytes) -> bytes:
    return (
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
        + content
        + b"\nendstream"
    )


def _write_pdf_objects(path: Path, objects: list[bytes]) -> None:
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f\n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n\n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(output)


def _print_table(rows: list[ComparisonRow]) -> None:
    print(
        "alpha | chaining success m/t | chaining failure m/t | "
        "linear success m/t | linear failure m/t"
    )
    for row in rows:
        print(
            f"{row.actual_load:.1f} | "
            f"{row.chaining_success_measured:.3f}/{row.chaining_success_theory:.3f} | "
            f"{row.chaining_failure_measured:.3f}/{row.chaining_failure_theory:.3f} | "
            f"{row.linear_success_measured:.3f}/{row.linear_success_theory:.3f} | "
            f"{row.linear_failure_measured:.3f}/{row.linear_failure_theory:.3f}"
        )


def run_experiment() -> list[ComparisonRow]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    data_rng = random.Random(DATA_SEED)
    max_items = round(max(LOAD_FACTORS) * CAPACITY)
    urls = [_make_url(data_rng, index) for index in range(max_items)]
    query_rng = random.Random(QUERY_SEED)
    rows = [
        _measure_load_factor(load_factor, urls, query_rng)
        for load_factor in LOAD_FACTORS
    ]
    _write_csv(rows)
    _write_svg(rows)
    _write_pdf(rows)
    _print_table(rows)
    return rows


if __name__ == "__main__":
    run_experiment()
