"""Utility helpers to safely log statistics to Weights & Biases."""
from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np

try:  # pragma: no cover - torch may be unavailable in minimal environments
    import torch
except ImportError:  # pragma: no cover
    torch = None

_MAX_SERIALIZABLE_ARRAY_ELEMENTS = 1024
_SEQUENCE_SUMMARY_HEAD = 5
_SEQUENCE_SUMMARY_TAIL = 5


def _is_wandb_media(value: Any) -> bool:
    """Return True if the object is a wandb media/artifact that should be logged as-is."""

    return hasattr(value, "_json_id") or getattr(value, "_wandb_asset_path", None) is not None


def _to_native_scalar(value: Any) -> Any:
    """Convert numpy scalar types to native Python scalars."""

    if isinstance(value, (np.generic,)):
        return value.item()
    return value


def _summarize_array(array: np.ndarray) -> Dict[str, Any]:
    """Produce a JSON-serializable summary for potentially large numpy arrays."""

    arr = np.asarray(array)
    summary: Dict[str, Any] = {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "size": int(arr.size),
    }

    if arr.size == 0:
        summary["values"] = []
        return summary

    flat = arr.reshape(-1)

    if np.issubdtype(arr.dtype, np.number):
        summary.update(
            {
                "min": _to_native_scalar(np.min(arr)),
                "max": _to_native_scalar(np.max(arr)),
                "mean": _to_native_scalar(np.mean(arr)),
            }
        )
        if arr.size > 1:
            summary["std"] = _to_native_scalar(np.std(arr))
        if np.issubdtype(arr.dtype, np.integer):
            summary["nonzero"] = int(np.count_nonzero(arr))
            summary["sum"] = _to_native_scalar(np.sum(arr))
    elif np.issubdtype(arr.dtype, np.bool_):
        true_count = int(np.count_nonzero(arr))
        summary.update(
            {
                "true_count": true_count,
                "false_count": int(arr.size - true_count),
                "nonzero": true_count,
            }
        )
    else:
        summary["sample"] = [str(item) for item in flat[: min(10, flat.size)]]

    if arr.size <= _MAX_SERIALIZABLE_ARRAY_ELEMENTS:
        if np.issubdtype(arr.dtype, np.number) or np.issubdtype(arr.dtype, np.bool_):
            summary["values"] = arr.tolist()
        else:
            summary["values"] = [str(item) for item in flat.tolist()]
    else:
        if "sample" not in summary:
            if np.issubdtype(arr.dtype, np.number) or np.issubdtype(arr.dtype, np.bool_):
                summary["sample"] = flat[: min(10, flat.size)].tolist()
            else:
                summary["sample"] = [str(item) for item in flat[: min(10, flat.size)]]

    return summary


def _sanitize_for_wandb(value: Any) -> Any:
    """Recursively convert values to wandb-friendly JSON-serializable structures."""

    if _is_wandb_media(value):
        return value

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, os.PathLike):
        return os.fspath(value)

    if isinstance(value, (np.generic,)):
        return value.item()

    if torch is not None and isinstance(value, torch.Tensor):
        return _sanitize_for_wandb(value.detach().cpu().numpy())

    if isinstance(value, np.ndarray):
        return _summarize_array(value)

    if isinstance(value, dict):
        return {str(k): _sanitize_for_wandb(v) for k, v in value.items()}

    if isinstance(value, list):
        if len(value) <= _MAX_SERIALIZABLE_ARRAY_ELEMENTS:
            return [_sanitize_for_wandb(v) for v in value]
        return {
            "length": len(value),
            "head": [_sanitize_for_wandb(v) for v in value[:_SEQUENCE_SUMMARY_HEAD]],
            "tail": [_sanitize_for_wandb(v) for v in value[-_SEQUENCE_SUMMARY_TAIL:]],
        }

    if isinstance(value, tuple):
        sanitized = _sanitize_for_wandb(list(value))
        if isinstance(sanitized, dict):
            sanitized["type"] = "tuple"
        return sanitized

    if isinstance(value, set):
        sample = list(value)
        sample_preview = sample[: _MAX_SERIALIZABLE_ARRAY_ELEMENTS]
        return {
            "length": len(value),
            "sample": [_sanitize_for_wandb(v) for v in sample_preview],
        }

    return str(value)


def sanitize_stats_for_wandb(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare stats dictionary for wandb logging by sanitizing complex objects."""

    return {k: _sanitize_for_wandb(v) for k, v in stats.items()}
