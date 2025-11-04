import sys
import types

import numpy as np


class _DummyModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__file__ = f"<stub {name}>"

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _noop(*args, **kwargs):
            return None

        return _noop


def _ensure_dummy_module(name):
    module = _DummyModule(name)
    sys.modules[name] = module
    return module


if "matplotlib" not in sys.modules:
    matplotlib = _DummyModule("matplotlib")
    matplotlib.pyplot = _DummyModule("matplotlib.pyplot")
    matplotlib.patches = _DummyModule("matplotlib.patches")
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = matplotlib.pyplot
    sys.modules["matplotlib.patches"] = matplotlib.patches

if "wandb" not in sys.modules:
    wandb = _DummyModule("wandb")
    wandb.Image = lambda *args, **kwargs: None
    sys.modules["wandb"] = wandb

if "sklearn" not in sys.modules:
    sklearn = _DummyModule("sklearn")
    sklearn_cluster = _DummyModule("sklearn.cluster")
    sklearn_metrics = _DummyModule("sklearn.metrics")
    sklearn_neighbors = _DummyModule("sklearn.neighbors")

    class _DummyKMeans:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            return self

        def predict(self, *args, **kwargs):
            return []

    def _zero(*args, **kwargs):
        return 0.0

    class _DummyNearestNeighbors:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            return self

        def kneighbors(self, *args, **kwargs):
            return np.array([[0]]), np.array([[0.0]])

    sklearn_cluster.KMeans = _DummyKMeans
    sklearn_metrics.average_precision_score = _zero
    sklearn_metrics.balanced_accuracy_score = _zero
    sklearn_metrics.confusion_matrix = lambda *args, **kwargs: np.array([[1, 0], [0, 1]])
    sklearn_metrics.precision_recall_curve = lambda *args, **kwargs: (
        np.array([0.0]),
        np.array([0.0]),
        np.array([0.0]),
    )
    sklearn_metrics.roc_auc_score = _zero

    sklearn.cluster = sklearn_cluster
    sklearn.metrics = sklearn_metrics
    sklearn.neighbors = sklearn_neighbors
    sklearn_neighbors.NearestNeighbors = _DummyNearestNeighbors
    sys.modules["sklearn"] = sklearn
    sys.modules["sklearn.cluster"] = sklearn_cluster
    sys.modules["sklearn.metrics"] = sklearn_metrics
    sys.modules["sklearn.neighbors"] = sklearn_neighbors

if "psycopg2" not in sys.modules:
    psycopg2 = _DummyModule("psycopg2")

    class _DummyCursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

        def close(self):
            return None

    class _DummyConnection:
        def cursor(self):
            return _DummyCursor()

        def close(self):
            return None

    psycopg2.connect = lambda *args, **kwargs: _DummyConnection()
    sys.modules["psycopg2"] = psycopg2

if "tqdm" not in sys.modules:
    tqdm_module = _DummyModule("tqdm")
    tqdm_module.tqdm = lambda iterable=None, *args, **kwargs: iterable
    sys.modules["tqdm"] = tqdm_module

if "networkx" not in sys.modules:
    networkx = _DummyModule("networkx")

    class _DummyGraph:
        pass

    networkx.Graph = _DummyGraph
    sys.modules["networkx"] = networkx

if "yacs" not in sys.modules:
    yacs = _DummyModule("yacs")
    yacs_config = _DummyModule("yacs.config")

    class _DummyCfgNode(dict):
        def __getattr__(self, item):
            return self.get(item)

        def clone(self):
            return _DummyCfgNode(self)

        def merge_from_other_cfg(self, other):
            self.update(other)

    yacs_config.CfgNode = _DummyCfgNode
    yacs.config = yacs_config
    sys.modules["yacs"] = yacs
    sys.modules["yacs.config"] = yacs_config

if "torch_geometric" not in sys.modules:
    torch_geometric = _DummyModule("torch_geometric")
    torch_geometric_data = _DummyModule("torch_geometric.data")

    class _DummyData:
        pass

    class _DummyTemporalData:
        pass

    torch_geometric_data.Data = _DummyData
    torch_geometric_data.TemporalData = _DummyTemporalData
    torch_geometric.data = torch_geometric_data
    sys.modules["torch_geometric"] = torch_geometric
    sys.modules["torch_geometric.data"] = torch_geometric_data

from pidsmaker.detection.evaluation_methods import node_evaluation


def test_build_malicious_node_checker_handles_mixed_types(monkeypatch):
    raw_ids = {1, "2", 3.0, "004", "5.0", "A-17"}

    def fake_ground_truth(cfg):
        return raw_ids, {}

    monkeypatch.setattr(
        node_evaluation, "get_ground_truth_nids", lambda cfg: fake_ground_truth(cfg)
    )

    checker, _, tokens = node_evaluation._build_malicious_node_checker(object())

    assert checker(1)
    assert checker(np.int64(1))
    assert checker("1")

    assert checker("2")
    assert checker(2)

    assert checker(3)
    assert checker(3.0)

    assert checker("004")
    assert checker(4)

    assert checker("5.0")
    assert checker("5")
    assert checker(5)

    assert checker("A-17")

    assert not checker("123.45")
    assert not checker("foo")
    assert not checker(np.nan)

    assert tokens == {str(x) for x in raw_ids}
