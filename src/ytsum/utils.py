from typing import Iterable


def convert_timestamp_to_ms(timestamp: str) -> int:
    """
    Convert a timestamp string to milliseconds.

    Args:
        timestamp (str): Timestamp in format "HH:MM:SS.mmm" or "HH:MM:SS:mmm" or "HH_MM_SS_mmm".

    Returns:
        int: Time in milliseconds.
    """
    parts = timestamp.replace(".", ":").replace("_", ":").split(":")
    h, m, s, ms = parts
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


def batched(iterable: Iterable, n: int = 1) -> Iterable:
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]
