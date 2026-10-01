"""Tests for enqueue failure diagnostics helpers."""

import enqueue_diagnostics as ed


def test_best_filename_ratio_scene_name():
    ratio = ed.best_filename_ratio(
        "Killer (original mix).flac",
        "04 - ATB - Killer (Original Mix).flac",
        "Killer",
        0.8,
    )
    assert ratio >= 0.8


def test_album_filename_analysis_counts_partial_match():
    tracks = [{"title": "Killer (original mix)"}, {"title": "Killer (totally different name)"}]
    slskd = [{"filename": "04 - ATB - Killer (Original Mix).flac"}, {"filename": "02 - unrelated.flac"}]
    analysis = ed.album_filename_analysis(tracks, slskd, "flac", "Killer", 0.8)
    assert analysis["total"] == 2
    assert analysis["matched"] == 1
    assert analysis["worst_ratio"] < 0.8


def test_release_diag_label():
    release = {"trackCount": 4, "country": ["Germany"], "format": "CD"}
    assert ed.release_diag_label(release) == "4t Germany CD"


def test_album_failure_report_emit(caplog):
    report = ed.AlbumEnqueueFailureReport("ATB", "Killer", 12)
    diag = ed.ReleaseEnqueueDiagnostics()
    diag.begin_release("4t Canada CD", 4)
    diag.note_track_count_mismatch("peer1", "Music\\ATB-Killer-CDM", 3, mixed_filetypes=False)
    report.add_release(diag)
    with caplog.at_level("WARNING"):
        report.emit(0.8)
    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "Enqueue failed: ATB - Killer" in msg
    assert "track_count_mismatch=1" in msg
    assert "closest_track_count" in msg
