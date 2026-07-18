import time

from sims_mod_manager.core.watcher import DownloadsWatcher


def test_scan_finds_only_mod_files(tmp_path):
    (tmp_path / "mod.zip").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")

    watcher = DownloadsWatcher(tmp_path, on_new_file=lambda path: None)

    assert watcher._scan() == {tmp_path / "mod.zip"}


def test_watcher_reports_new_file_exactly_once(tmp_path):
    seen = []
    watcher = DownloadsWatcher(tmp_path, on_new_file=seen.append, poll_interval_seconds=0.05)
    watcher.start()
    try:
        (tmp_path / "new_mod.package").write_bytes(b"x")
        deadline = time.time() + 2
        while time.time() < deadline and not seen:
            time.sleep(0.05)
        time.sleep(0.2)  # give one more poll cycle to prove it doesn't re-report
    finally:
        watcher.stop()

    assert seen == [tmp_path / "new_mod.package"]


def test_scan_on_missing_directory_returns_empty_set(tmp_path):
    missing_dir = tmp_path / "does_not_exist"
    watcher = DownloadsWatcher(missing_dir, on_new_file=lambda path: None)

    assert watcher._scan() == set()
