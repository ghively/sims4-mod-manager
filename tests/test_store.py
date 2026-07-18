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


def test_store_usable_from_a_different_thread(tmp_path):
    import threading

    store = ModStore(tmp_path / "store.db")
    errors = []

    def _use_from_thread():
        try:
            store.record_install(
                source="C:/Downloads/mod.zip",
                filename="mod.package",
                category="CAS",
                file_hash="fromthread",
                installed_path="C:/Mods/CAS/mod.package",
            )
        except Exception as exc:  # sqlite3.ProgrammingError if check_same_thread wasn't disabled
            errors.append(exc)

    thread = threading.Thread(target=_use_from_thread)
    thread.start()
    thread.join(timeout=5)

    assert errors == []
    assert store.is_duplicate("fromthread") is True
    store.close()


def test_store_survives_concurrent_writes_from_many_threads(tmp_path):
    import threading

    store = ModStore(tmp_path / "store.db")
    errors = []
    thread_count = 8

    # A Barrier holds every writer thread at the gate until all of them are
    # ready, so they all call execute()/commit() at (as close to) the same
    # instant -- rather than each thread running its single statement and
    # finishing well before the next one is even scheduled, which is not
    # decisive proof of anything since Python's bundled SQLite is often
    # already internally serialized regardless of the app-level lock.
    barrier = threading.Barrier(thread_count + 1)  # +1 for the reader thread below

    def _record(index: int) -> None:
        try:
            barrier.wait(timeout=5)
            store.record_install(
                source="C:/Downloads/mod.zip",
                filename=f"mod{index}.package",
                category="CAS",
                file_hash=f"hash{index}",
                installed_path=f"C:/Mods/CAS/mod{index}.package",
            )
        except Exception as exc:  # sqlite3.OperationalError ("database is locked")
            # without a lock serializing access, or connection corruption
            errors.append(exc)

    # A reader thread that hammers get_activity_log() *while* the writer
    # threads are still in flight (not after they've all joined) mirrors
    # the real ActivityTab-vs-InstallWorker scenario: ActivityTab.refresh()
    # can be called from the GUI thread at any moment, including mid-install.
    stop_reading = threading.Event()

    def _read_repeatedly() -> None:
        try:
            barrier.wait(timeout=5)
            while not stop_reading.is_set():
                store.get_activity_log()
        except Exception as exc:  # sqlite3.OperationalError ("database is locked")
            errors.append(exc)

    threads = [threading.Thread(target=_record, args=(i,)) for i in range(thread_count)]
    reader = threading.Thread(target=_read_repeatedly)

    reader.start()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    stop_reading.set()
    reader.join(timeout=5)

    assert errors == []
    log = store.get_activity_log()
    assert len(log) == thread_count
    assert {entry["filename"] for entry in log} == {
        f"mod{i}.package" for i in range(thread_count)
    }
    store.close()
