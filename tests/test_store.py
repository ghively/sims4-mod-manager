from sims_mod_manager.core.store import ModStore


def test_is_duplicate_false_before_any_record(tmp_path):
    store = ModStore(tmp_path / "store.db")
    assert store.is_duplicate("abc123") is False
    store.close()


def test_is_duplicate_true_after_record(tmp_path):
    store = ModStore(tmp_path / "store.db")
    store.record_install(
        source="C:/Downloads/mod.zip",
        filename="mod.package",
        category="CAS",
        file_hash="abc123",
        installed_path="C:/Mods/CAS/mod.package",
    )
    assert store.is_duplicate("abc123") is True
    store.close()


def test_activity_log_contains_recorded_install(tmp_path):
    store = ModStore(tmp_path / "store.db")
    store.record_install(
        source="C:/Downloads/mod.zip",
        filename="mod.package",
        category="CAS",
        file_hash="abc123",
        installed_path="C:/Mods/CAS/mod.package",
    )
    log = store.get_activity_log()
    assert len(log) == 1
    assert log[0]["filename"] == "mod.package"
    assert log[0]["category"] == "CAS"
    store.close()
