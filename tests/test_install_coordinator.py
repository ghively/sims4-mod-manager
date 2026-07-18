"""Thread-safety tests for InstallCoordinator (sims_mod_manager/gui/main_window.py).

InstallCoordinator is shared by both FindTab and InboxTab (via AppContext),
each driving it from its own background InstallWorker QThread. These tests
exercise the coordinator's locking directly -- no actual widgets are
constructed, so this is safe to run in the regular (headless) test suite
despite living next to a GUI module; PySide6 is already a project
dependency so the import works everywhere the app runs.
"""
import threading
import zipfile

from sims_mod_manager.core.store import ModStore
from sims_mod_manager.gui.main_window import InstallCoordinator


def _make_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)


def test_concurrent_installs_from_both_tabs_are_serialized(tmp_path):
    """Reproduces the exact race from the task-review finding: two threads
    (standing in for FindTab's and InboxTab's separate InstallWorker
    QThreads) both call coordinator.install() with different source files
    whose mod filename resolves to the same target path in the same
    category (so content-hash dedupe can't short-circuit either one).

    Without the lock around InstallCoordinator.install(), this can:
      1. race backup_mod_folders() (both threads see
         _backed_up_this_session as False and both back up), and/or
      2. race install_mod_file()'s _resolve_collision() TOCTOU check, with
         one shutil.copy2() silently clobbering the other's file.
    With the lock, install() runs fully sequentially across threads, so
    both files must survive with their own distinct content, and exactly
    one backup must be created.
    """
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    first_zip = downloads_dir / "hair_a.zip"
    _make_zip(first_zip, {"HairModA/somefile.package": "content a"})

    second_zip = downloads_dir / "hair_b.zip"
    _make_zip(second_zip, {"HairModB/somefile.package": "content b"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    sims4_dir = tmp_path / "Sims4"
    backup_dir = tmp_path / "Backups"
    store = ModStore(tmp_path / "store.db")

    coordinator = InstallCoordinator(
        mods_dir=mods_dir,
        staging_dir=staging_dir,
        store=store,
        sims4_dir=sims4_dir,
        backup_dir=backup_dir,
    )

    # A Barrier makes both threads call .install() at (as close to)
    # the same instant as possible, maximizing the chance of exposing the
    # race if the lock were absent or broken.
    barrier = threading.Barrier(2)
    results = {}
    errors = []

    def _install(key, source_path):
        try:
            barrier.wait(timeout=5)
            results[key] = coordinator.install(source_path)
        except Exception as exc:  # pragma: no cover - failure path only
            errors.append(exc)

    thread_a = threading.Thread(target=_install, args=("a", first_zip))
    thread_b = threading.Thread(target=_install, args=("b", second_zip))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)

    assert errors == []
    assert set(results) == {"a", "b"}

    result_a = results["a"]
    result_b = results["b"]
    assert result_a.errors == []
    assert result_b.errors == []
    assert len(result_a.installed) == 1
    assert len(result_b.installed) == 1

    installed_paths = [result_a.installed[0], result_b.installed[0]]
    names = {path.name for path in installed_paths}
    assert names == {"somefile.package", "somefile (2).package"}
    for path in installed_paths:
        assert path.parent == mods_dir / "CAS"

    # Both files survive on disk with correct, distinct content -- proving
    # _resolve_collision's check-then-copy never overlapped between the
    # two threads.
    contents_by_path = {path: path.read_bytes() for path in installed_paths}
    assert set(contents_by_path.values()) == {b"content a", b"content b"}

    # Backup-check-and-run was serialized too: exactly one backup zip
    # exists, and the session flag ended up True (not clobbered back to
    # False by a losing thread after a winning thread already flipped it).
    assert coordinator._backed_up_this_session is True
    backup_files = list(backup_dir.glob("*.zip"))
    assert len(backup_files) == 1

    store.close()
