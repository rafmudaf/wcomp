"""
A minimal disk cache used to avoid re-running the (slow, noisy) wake model
solvers every time the documentation dashboard is rebuilt.

Results are pickled to disk keyed by a caller-provided string key. This is
intentionally simple: callers are responsible for choosing a key that
uniquely identifies the inputs to their computation (for example, the case
directory name and the software name).
"""

import pickle
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Callable


@contextmanager
def quiet():
    """
    Context manager that discards anything written to stdout/stderr.

    The wake model solvers integrated in `wcomp` (FLORIS, FOXES, PyWake) print or log
    progress bars and per-chunk solver status directly to the console. This is useful
    when developing but clutters generated documentation. Wrap solver calls in this
    context manager to silence that output without changing any solver configuration.
    """
    buffer = StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        yield


class DiskCache:
    """
    A simple, unstructured pickle cache with a single directory of files.

    Args:
        cache_dir (str | Path): Directory where cached results are stored.
            It is created if it does not already exist.
    """

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        return self.cache_dir / f"{key}.pkl"

    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """
        Return the cached result for `key` if present, otherwise call
        `compute_fn`, cache its return value, and return it.

        Args:
            key (str): Unique identifier for this computation.
            compute_fn (Callable[[], Any]): Zero-argument callable that produces
                a picklable result when there is no cache hit.

        Returns:
            Any: The cached or newly computed result.
        """
        cache_file = self._path_for(key)
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                return pickle.load(f)

        result = compute_fn()
        with open(cache_file, "wb") as f:
            pickle.dump(result, f)
        return result
