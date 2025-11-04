 import json

import numpy as np

from pidsmaker.utils.wandb_logging import sanitize_stats_for_wandb


class _DummyMedia:
    def __init__(self):
        self._json_id = "dummy-media:1"


class _NonSerializable:
    pass


def test_sanitize_stats_for_wandb_handles_mixed_values():
    stats = {
        "theta": np.float64(0.42),
        "predictions": np.array([0, 1, 0, 1], dtype=np.int64),
        "metadata": {"nested": np.array([[0.1, 0.2], [0.3, 0.4]])},
        "media": _DummyMedia(),
        "object": _NonSerializable(),
        "path": __file__,
    }

    sanitized = sanitize_stats_for_wandb(stats)

    assert isinstance(sanitized["theta"], float)
    assert sanitized["predictions"]["shape"] == [4]
    assert sanitized["predictions"]["nonzero"] == 2
    assert sanitized["metadata"]["nested"]["shape"] == [2, 2]
    assert sanitized["media"] is stats["media"]
    assert isinstance(sanitized["object"], str)
    assert isinstance(sanitized["path"], str)

    # Ensure nested dictionary is JSON serializable after removing wandb media
    sanitized_without_media = dict(sanitized)
    sanitized_without_media.pop("media")
    json.dumps(sanitized_without_media)


def test_sanitize_stats_for_wandb_large_sequences_and_booleans():
    large_list = list(range(2000))
    bool_array = np.array([True, False, True, True])
    tuple_value = (1, 2, 3)
    set_value = {"alpha", "beta", "gamma"}

    stats = {
        "large_list": large_list,
        "bool_array": bool_array,
        "tuple": tuple_value,
        "set": set_value,
    }

    sanitized = sanitize_stats_for_wandb(stats)

    large_list_summary = sanitized["large_list"]
    assert large_list_summary["length"] == len(large_list)
    assert large_list_summary["head"] == list(range(5))
    assert large_list_summary["tail"] == list(range(len(large_list) - 5, len(large_list)))

    bool_summary = sanitized["bool_array"]
    assert bool_summary["shape"] == [4]
    assert bool_summary["true_count"] == 3
    assert bool_summary["false_count"] == 1
    assert bool_summary["nonzero"] == 3

    tuple_summary = sanitized["tuple"]
    assert tuple_summary == [1, 2, 3]

    set_summary = sanitized["set"]
    assert set_summary["length"] == len(set_value)
    assert set(set_summary["sample"]).issubset(set_value)
