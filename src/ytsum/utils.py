from typing import Iterable, List, Tuple


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


def format_elapsed_time(start_time: float, end_time: float) -> str:
    elapsed_seconds: float = end_time - start_time
    minutes_seconds: Tuple[int, float] = divmod(elapsed_seconds, 60)
    minutes: int = int(minutes_seconds[0])
    seconds: int = int(minutes_seconds[1])
    milliseconds: int = int((elapsed_seconds - int(elapsed_seconds)) * 1000)

    parts: List[str] = []
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    if milliseconds > 0:
        parts.append(f"{milliseconds} millisecond{'s' if milliseconds != 1 else ''}")

    if len(parts) > 1:
        return f"{', '.join(parts[:-1])} and {parts[-1]}"
    elif len(parts) == 1:
        return parts[0]
    else:
        return "0 milliseconds"
