"""Draw the relational ERD to ERD/erd.png (for the PDF report).

Run from the repo root:  python ERD/draw_erd.py
The same diagram is kept as Mermaid in ERD/README.md for GitHub.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent / "erd.png"

HEADER_H = 0.55
ROW_H = 0.42
WIDTH = 4.4

# (name, x, top_y, [(key, column, type), ...])
TABLES = {
    "holidays": (0.4, 7.6, [
        ("PK", "id", "INT AUTO_INCREMENT"),
        ("UK", "name", "VARCHAR(64) NOT NULL"),
    ]),
    "weather_conditions": (0.4, 3.9, [
        ("PK", "id", "INT AUTO_INCREMENT"),
        ("UK", "weather_main", "VARCHAR(32) NOT NULL"),
        ("UK", "weather_description", "VARCHAR(64) NOT NULL"),
    ]),
    "traffic_readings": (7.0, 8.4, [
        ("PK", "id", "INT AUTO_INCREMENT"),
        ("IX", "date_time", "DATETIME NOT NULL"),
        ("", "temp", "DOUBLE NOT NULL"),
        ("", "rain_1h", "DOUBLE NOT NULL"),
        ("", "snow_1h", "DOUBLE NOT NULL"),
        ("", "clouds_all", "INT NOT NULL"),
        ("", "traffic_volume", "INT NOT NULL"),
        ("FK", "holiday_id", "INT NULL"),
        ("FK", "weather_id", "INT NOT NULL"),
    ]),
}

KEY_COLORS = {"PK": "#b45309", "FK": "#1d4ed8", "UK": "#047857", "IX": "#6b7280"}


def draw_table(ax, name, x, top, columns):
    """Draw one table box and return {column: (left_x, right_x, mid_y)}."""
    height = HEADER_H + ROW_H * len(columns)
    ax.add_patch(FancyBboxPatch((x, top - height), WIDTH, height,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                fc="white", ec="#1f2937", lw=1.4))
    ax.add_patch(FancyBboxPatch((x, top - HEADER_H), WIDTH, HEADER_H,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#1f2937", ec="#1f2937", lw=1.4))
    ax.text(x + WIDTH / 2, top - HEADER_H / 2, name, ha="center", va="center",
            color="white", fontsize=11, fontweight="bold", family="monospace")

    anchors = {}
    for i, (key, col, typ) in enumerate(columns):
        y = top - HEADER_H - ROW_H * (i + 0.5)
        if i:
            ax.plot([x, x + WIDTH], [y + ROW_H / 2] * 2, color="#e5e7eb", lw=0.8)
        if key:
            ax.text(x + 0.12, y, key, va="center", fontsize=8, fontweight="bold",
                    color=KEY_COLORS[key], family="monospace")
        ax.text(x + 0.55, y, col, va="center", fontsize=9.5, family="monospace",
                fontweight="bold" if key == "PK" else "normal")
        ax.text(x + WIDTH - 0.12, y, typ, va="center", ha="right", fontsize=7.5,
                color="#4b5563", family="monospace")
        anchors[col] = (x, x + WIDTH, y)
    return anchors


def crow_foot(ax, x, y, direction):
    """'Many' end: three prongs opening towards the table at x."""
    for dy in (-0.16, 0, 0.16):
        ax.plot([x + direction * 0.3, x], [y, y + dy], color="#1f2937", lw=1.2)


def bar(ax, x, y, optional=False):
    """'One' end: a single bar, or a circle + bar for zero-or-one."""
    ax.plot([x, x], [y - 0.15, y + 0.15], color="#1f2937", lw=1.2)
    if optional:
        ax.add_patch(plt.Circle((x + 0.22, y), 0.08, fc="white", ec="#1f2937", lw=1.2))


def relate(ax, parent, child, label, optional, elbow_x, label_above=True):
    """Draw parent.id (one) -> child FK (many) with an orthogonal elbow."""
    (_, px, py), (cx, _, cy) = parent, child
    ax.plot([px, elbow_x, elbow_x, cx], [py, py, cy, cy], color="#1f2937", lw=1.2, zorder=0)
    bar(ax, px + 0.12, py, optional=optional)
    crow_foot(ax, cx, cy, -1)
    # keep the label on the side away from the vertical part of the elbow
    ax.text(px + 0.45, py + (0.12 if label_above else -0.12), label, fontsize=8,
            color="#374151", style="italic", va="bottom" if label_above else "top")


def main():
    fig, ax = plt.subplots(figsize=(12, 7.2))
    ax.set_xlim(0, 11.8)
    ax.set_ylim(1.6, 9.2)
    ax.axis("off")

    anchors = {name: draw_table(ax, name, x, top, cols)
               for name, (x, top, cols) in TABLES.items()}

    relate(ax, anchors["holidays"]["id"], anchors["traffic_readings"]["holiday_id"],
           "0..1 holiday : N readings", optional=True, elbow_x=5.9)
    relate(ax, anchors["weather_conditions"]["id"], anchors["traffic_readings"]["weather_id"],
           "1 condition : N readings", optional=False, elbow_x=6.4,
           label_above=False)

    ax.text(5.9, 9.0, "Metro Interstate Traffic Volume - Entity Relationship Diagram",
            ha="center", fontsize=13, fontweight="bold")
    ax.text(0.4, 1.8, "PK primary key   FK foreign key   UK unique   IX indexed",
            fontsize=8.5, color="#4b5563", family="monospace")

    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
