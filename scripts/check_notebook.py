"""Execute every EDA code cell headlessly from the repository root."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.chdir(ROOT)
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Render each figure instead of asking a noninteractive backend to open a window.
    def render_figures():
        for number in plt.get_fignums():
            plt.figure(number).canvas.draw()
        plt.close("all")

    plt.show = render_figures
    notebook = json.loads((ROOT / "notebooks/01_eda.ipynb").read_text(encoding="utf-8"))
    namespace = {"__name__": "__notebook__"}
    count = 0
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), f"01_eda.ipynb:cell{i}", "exec"), namespace)
            count += 1
    print(f"Executed {count} EDA code cells successfully (headless).")


if __name__ == "__main__":
    main()
