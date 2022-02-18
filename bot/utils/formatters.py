from typing import Union

from bot.core import constants


def color_level(value: float, low: float = constants.low_latency, high: float = constants.high_latency) -> int:
    """Return the color intensity of a value."""
    if value < low:
        return constants.colours.bright_green
    elif value < high:
        return constants.colours.orange
    else:
        return constants.colours.red


def format_bytes(num: Union[int, float], metric: bool = False, precision: int = 1) -> str:
    """
    Human-readable formatting of bytes, using binary (powers of 1024) or metric (powers of 1000) representation.

    Args:
        metric: Use metric representation.
        num: Number to format.
        precision (int): Number of decimal places to display (0-3).
    """
    metric_labels = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    binary_labels = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    precision_offsets = [0.5, 0.05, 0.005, 0.0005]
    precision_formats = ["{}{:.0f} {}", "{}{:.1f} {}", "{}{:.2f} {}", "{}{:.3f} {}"]

    unit_labels = metric_labels if metric else binary_labels
    last_label = unit_labels[-1]
    unit_step = 1000 if metric else 1024
    unit_step_thresh = unit_step - precision_offsets[precision]

    is_negative = num < 0
    if is_negative:  # Faster than ternary assignment or always running abs().
        num = abs(num)

    unit = ""
    for unit in unit_labels:
        if num < unit_step_thresh:
            # Only accepts the current unit if we're BELOW the threshold where
            # float rounding behavior would place us into the NEXT unit.
            break
        if unit != last_label:
            # Only shrink the number if we haven't reached the last unit.
            num /= unit_step

    return precision_formats[precision].format("-" if is_negative else "", num, unit)
