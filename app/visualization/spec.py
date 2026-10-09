from typing import Any

def build_bar_chart(labels: list[str], values: list[float], title: str,
                    x_title: str = "", y_title: str = "") -> dict[str, Any]:
    if len(labels) != len(values):
        raise ValueError("labels and values must have the same length")
    return {"data": [{"type": "bar", "x": labels, "y": values}],
            "layout": {"title": title, "xaxis": {"title": x_title}, "yaxis": {"title": y_title}}}
