from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
INITIAL_CSV = OUTPUT_DIR / "initial_archive.csv"
FINAL_CSV = OUTPUT_DIR / "final_archive.csv"
PLOT_PATH = OUTPUT_DIR / "archive_comparison_hv.png"

REFERENCE_F1 = 1.1
REFERENCE_F2 = 1.1


def load_archive(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = {
        "archive_index",
        "chromosome",
        "f1",
        "f2",
        "norm_f1",
        "norm_f2",
        "strength",
        "raw_fitness",
        "density",
        "total_fitness",
    }

    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {csv_path.name}: {sorted(missing)}")

    return df


def non_dominated_mask(df: pd.DataFrame, x_col: str, y_col: str) -> pd.Series:
    xs = df[x_col].to_numpy()
    ys = df[y_col].to_numpy()

    mask = []
    for i in range(len(df)):
        dominated = False
        for j in range(len(df)):
            if i == j:
                continue

            better_or_equal = xs[j] <= xs[i] and ys[j] <= ys[i]
            strictly_better = xs[j] < xs[i] or ys[j] < ys[i]

            if better_or_equal and strictly_better:
                dominated = True
                break

        mask.append(not dominated)

    return pd.Series(mask, index=df.index)


def prepare_front(df: pd.DataFrame, x_col: str, y_col: str) -> pd.DataFrame:
    nd = df[non_dominated_mask(df, x_col, y_col)].copy()
    nd = nd.sort_values(by=x_col, ascending=True).reset_index(drop=True)
    return nd


def compute_hypervolume_2d(front: pd.DataFrame, x_col: str, y_col: str,
                           ref_x: float, ref_y: float) -> float:
    hv = 0.0
    current_upper_y = ref_y

    for _, row in front.iterrows():
        x = row[x_col]
        y = row[y_col]

        if y < current_upper_y:
            width = ref_x - x
            height = current_upper_y - y
            if width > 0 and height > 0:
                hv += width * height
            current_upper_y = y

    return hv


def plot_raw_space(ax, df: pd.DataFrame, title: str):
    ax.scatter(df["f1"], df["f2"], alpha=0.75, s=35, label="Archive individuals")

    front = prepare_front(df, "f1", "f2")
    ax.scatter(front["f1"], front["f2"], color="red", s=50, label="Non-dominated")
    ax.plot(front["f1"], front["f2"], linestyle="--", linewidth=1)

    ax.set_title(title)
    ax.set_xlabel("f1")
    ax.set_ylabel("f2")
    ax.grid(True, alpha=0.3)
    ax.legend()

    return front


def plot_hv_space(ax, df: pd.DataFrame, title: str, ref_x: float, ref_y: float):
    ax.scatter(df["norm_f1"], df["norm_f2"], alpha=0.75, s=35, label="Archive individuals")

    front = prepare_front(df, "norm_f1", "norm_f2")
    ax.scatter(front["norm_f1"], front["norm_f2"], color="red", s=50, label="Non-dominated")
    ax.plot(front["norm_f1"], front["norm_f2"], linestyle="--", linewidth=1, color="red")

    # Reference point
    ax.scatter([ref_x], [ref_y], marker="x", s=90, linewidths=2, label="HV reference point")

    # Hypervolume rectangles
    current_upper_y = ref_y
    for _, row in front.iterrows():
        x = row["norm_f1"]
        y = row["norm_f2"]

        if y < current_upper_y:
            width = ref_x - x
            height = current_upper_y - y
            if width > 0 and height > 0:
                rect = Rectangle(
                    (x, y),
                    width,
                    height,
                    fill=False,
                    linestyle=":",
                    linewidth=1
                )
                ax.add_patch(rect)
            current_upper_y = y

    hv = compute_hypervolume_2d(front, "norm_f1", "norm_f2", ref_x, ref_y)
    hv_ratio = hv / (ref_x * ref_y)

    ax.set_title(title)
    ax.set_xlabel("norm_f1 (HV space)")
    ax.set_ylabel("norm_f2 (HV space)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Keep the HV space visible
    x_max = max(ref_x + 0.03, df["norm_f1"].max() + 0.05)
    y_max = max(ref_y + 0.03, df["norm_f2"].max() + 0.05)
    ax.set_xlim(left=min(-0.02, df["norm_f1"].min() - 0.02), right=x_max)
    ax.set_ylim(bottom=min(-0.02, df["norm_f2"].min() - 0.02), top=y_max)

    text = (
        f"ND count: {len(front)}\n"
        f"HV: {hv:.6f}\n"
        f"HV ratio: {hv_ratio:.6f}"
    )
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round", alpha=0.15)
    )

    return front, hv, hv_ratio


def archive_stats(df: pd.DataFrame, label: str) -> dict:
    pearson = df[["f1", "f2"]].corr(method="pearson").iloc[0, 1]
    spearman = df[["f1", "f2"]].corr(method="spearman").iloc[0, 1]

    nd_raw = prepare_front(df, "f1", "f2")
    nd_hv = prepare_front(df, "norm_f1", "norm_f2")

    stats = {
        "label": label,
        "count": len(df),
        "pearson": pearson,
        "spearman": spearman,
        "nd_raw_count": len(nd_raw),
        "nd_hv_count": len(nd_hv),
        "best_f1": df["f1"].min(),
        "best_f2": df["f2"].min(),
    }
    return stats


def print_stats(stats: dict):
    print("=" * 60)
    print(stats["label"])
    print(f"Archive size            : {stats['count']}")
    print(f"Pearson corr(f1, f2)    : {stats['pearson']:.6f}")
    print(f"Spearman corr(f1, f2)   : {stats['spearman']:.6f}")
    print(f"ND count (raw space)    : {stats['nd_raw_count']}")
    print(f"ND count (HV space)     : {stats['nd_hv_count']}")
    print(f"Best f1                 : {stats['best_f1']:.6f}")
    print(f"Best f2                 : {stats['best_f2']:.6f}")


def main():
    initial_df = load_archive(INITIAL_CSV)
    final_df = load_archive(FINAL_CSV)

    initial_stats = archive_stats(initial_df, "INITIAL ARCHIVE")
    final_stats = archive_stats(final_df, "FINAL ARCHIVE")

    print_stats(initial_stats)
    print_stats(final_stats)

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    initial_front_raw = plot_raw_space(
        axes[0, 0],
        initial_df,
        "Initial Archive - Raw Objective Space"
    )

    final_front_raw = plot_raw_space(
        axes[0, 1],
        final_df,
        "Final Archive - Raw Objective Space"
    )

    # Hypervolume space normalization
    # Instead of fixed reference point, use normalized bounds [0, 1.1]
    # The reference point in normalized space is usually (1.1, 1.1)
    ref_x = 1.1
    ref_y = 1.1

    initial_front_hv, initial_hv, initial_hv_ratio = plot_hv_space(
        axes[1, 0],
        initial_df,
        "Initial Archive - Hypervolume Space",
        ref_x,
        ref_y
    )

    final_front_hv, final_hv, final_hv_ratio = plot_hv_space(
        axes[1, 1],
        final_df,
        "Final Archive - Hypervolume Space",
        ref_x,
        ref_y
    )

    summary = (
        f"Initial Pearson: {initial_stats['pearson']:.4f} | "
        f"Initial Spearman: {initial_stats['spearman']:.4f} | "
        f"Initial ND(raw): {len(initial_front_raw)} | Initial HV ratio: {initial_hv_ratio:.4f}\n"
        f"Final Pearson: {final_stats['pearson']:.4f} | "
        f"Final Spearman: {final_stats['spearman']:.4f} | "
        f"Final ND(raw): {len(final_front_raw)} | Final HV ratio: {final_hv_ratio:.4f}"
    )

    fig.suptitle("Initial vs Final Archive Analysis", fontsize=16)
    fig.text(0.5, 0.01, summary, ha="center", va="bottom")

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Also save as latest for easy access
    latest_path = OUTPUT_DIR / "archive_comparison_latest.png"
    plt.savefig(latest_path, dpi=300, bbox_inches='tight')
    # plt.show() # Commented out to avoid blocking in non-interactive environments

    for candidate in OUTPUT_DIR.glob("archive_comparison_*.png"):
        if candidate.name == "archive_comparison_latest.png":
            continue
        candidate.unlink(missing_ok=True)

    print(f"============================================================")
    print(f"Latest plot updated at: {latest_path}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
