import pytest

from pidsmaker.config.pipeline import get_runtime_required_args, get_default_cfg


def test_db_host_port_overrides_applied():
    # Provide a minimal set of args: model and dataset are required positional args
    argv = ["orthrus", "CADETS_E3", "--db_host", "1.2.3.4", "--db_port", "9999"]
    args = get_runtime_required_args(False, argv)
    cfg = get_default_cfg(args)

    assert hasattr(cfg, "database")
    assert cfg.database.host == "1.2.3.4"
    assert cfg.database.port == "9999"
*** End Patch