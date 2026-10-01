"""Enqueue failure diagnostics (no slskd/lidarr dependencies)."""

from __future__ import annotations

import difflib
import logging

logger = logging.getLogger("soularr")


def folder_tail(file_dir: str, max_len: int = 72) -> str:
    tail = file_dir.replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]
    if len(tail) > max_len:
        return "…" + tail[-max_len + 1 :]
    return tail


class ReleaseEnqueueDiagnostics:
    """Collects why peer folders did not enqueue for one Lidarr release attempt."""

    __slots__ = (
        "release_label",
        "wanted_track_count",
        "folders_checked",
        "track_count_mismatch",
        "mixed_filetypes_in_folder",
        "filename_mismatch",
        "match_enqueue_failed",
        "_closest_count",
        "_best_filename_near",
    )

    def __init__(self) -> None:
        self.release_label = "?"
        self.wanted_track_count = 0
        self.folders_checked = 0
        self.track_count_mismatch = 0
        self.mixed_filetypes_in_folder = 0
        self.filename_mismatch = 0
        self.match_enqueue_failed = 0
        self._closest_count = None
        self._best_filename_near = None

    def begin_release(self, release_label: str, wanted_track_count: int) -> None:
        self.release_label = release_label
        self.wanted_track_count = wanted_track_count

    def note_folder_checked(self) -> None:
        self.folders_checked += 1

    def note_track_count_mismatch(self, username: str, file_dir: str, peer_count: int, mixed_filetypes: bool) -> None:
        if mixed_filetypes:
            self.mixed_filetypes_in_folder += 1
        else:
            self.track_count_mismatch += 1
        if peer_count <= 0:
            return
        diff = abs(peer_count - self.wanted_track_count)
        if self._closest_count is None or diff < self._closest_count[0]:
            self._closest_count = (diff, username, folder_tail(file_dir), peer_count)

    def note_filename_mismatch(
        self,
        username: str,
        file_dir: str,
        matched: int,
        total: int,
        worst_ratio: float,
        worst_track: str,
        worst_peer_file: str,
    ) -> None:
        self.filename_mismatch += 1
        if self._best_filename_near is None or worst_ratio > self._best_filename_near[2]:
            self._best_filename_near = (
                matched,
                total,
                worst_ratio,
                username,
                folder_tail(file_dir),
                worst_track,
                worst_peer_file,
            )

    def note_match_enqueue_failed(self, username: str, file_dir: str, reason: str) -> None:
        self.match_enqueue_failed += 1
        logger.warning(
            f"Match ok but slskd enqueue failed: user={username} folder={folder_tail(file_dir)} reason={reason}"
        )


class AlbumEnqueueFailureReport:
    """One WARNING summary per album when no release could be enqueued."""

    def __init__(self, artist_name: str, album_name: str, search_peer_count: int) -> None:
        self.artist_name = artist_name
        self.album_name = album_name
        self.search_peer_count = search_peer_count
        self.release_attempts: list[ReleaseEnqueueDiagnostics] = []

    def add_release(self, diag: ReleaseEnqueueDiagnostics) -> None:
        self.release_attempts.append(diag)

    def emit(self, minimum_match_ratio: float) -> None:
        if not self.release_attempts:
            logger.warning(f"Enqueue failed: {self.artist_name} - {self.album_name} | no release attempts recorded")
            return

        track_mm = sum(d.track_count_mismatch for d in self.release_attempts)
        mixed = sum(d.mixed_filetypes_in_folder for d in self.release_attempts)
        fname_mm = sum(d.filename_mismatch for d in self.release_attempts)
        enq_fail = sum(d.match_enqueue_failed for d in self.release_attempts)
        folders = sum(d.folders_checked for d in self.release_attempts)
        release_labels = ", ".join(d.release_label for d in self.release_attempts)

        parts = [
            f"Enqueue failed: {self.artist_name} - {self.album_name}",
            f"search_peers={self.search_peer_count}",
            f"releases_tried={len(self.release_attempts)}",
            f"folders_checked={folders}",
            f"track_count_mismatch={track_mm}",
            f"mixed_filetypes={mixed}",
            f"filename_mismatch={fname_mm}",
            f"match_enqueue_failed={enq_fail}",
            f"min_filename_ratio={minimum_match_ratio}",
            f"releases=[{release_labels}]",
        ]

        closest = None
        closest_diff = None
        for d in self.release_attempts:
            if d._closest_count and (closest_diff is None or d._closest_count[0] < closest_diff):
                closest_diff = d._closest_count[0]
                closest = (d._closest_count, d.wanted_track_count)

        if closest:
            diff, user, folder, peer_count = closest[0]
            wanted = closest[1]
            parts.append(
                f"closest_track_count: user={user} folder={folder} peer_files={peer_count} lidarr_tracks={wanted} delta={diff}"
            )

        best_fn = None
        best_ratio = -1.0
        for d in self.release_attempts:
            if d._best_filename_near and d._best_filename_near[2] > best_ratio:
                best_ratio = d._best_filename_near[2]
                best_fn = (d._best_filename_near, d.wanted_track_count, d.release_label)

        if best_fn:
            matched, total, worst_ratio, user, folder, worst_track, worst_file = best_fn[0]
            parts.append(
                "best_filename_near: "
                f"release={best_fn[2]} user={user} folder={folder} "
                f"matched={matched}/{total} worst_ratio={worst_ratio:.3f} "
                f"lidarr_track={worst_track!r} peer_file={worst_file!r}"
            )

        summary = " | ".join(parts)
        logger.warning(summary)
        if closest:
            diff, user, folder, peer_count = closest[0]
            wanted = closest[1]
            logger.info(
                f"Enqueue detail closest_track_count: user={user} folder={folder} "
                f"peer_files={peer_count} lidarr_tracks={wanted} delta={diff}"
            )
        if best_fn:
            matched, total, worst_ratio, user, folder, worst_track, worst_file = best_fn[0]
            logger.info(
                f"Enqueue detail best_filename_near: release={best_fn[2]} user={user} folder={folder} "
                f"matched={matched}/{total} worst_ratio={worst_ratio:.3f} "
                f"lidarr_track={worst_track!r} peer_file={worst_file!r}"
            )


def check_ratio(separator: str, ratio: float, lidarr_filename: str, slskd_filename: str, minimum_match_ratio: float) -> float:
    if ratio < minimum_match_ratio:
        if separator != "":
            lidarr_filename_word_count = len(lidarr_filename.split()) * -1
            truncated_slskd_filename = " ".join(slskd_filename.split(separator)[lidarr_filename_word_count:])
            ratio = difflib.SequenceMatcher(None, lidarr_filename, truncated_slskd_filename).ratio()
        else:
            ratio = difflib.SequenceMatcher(None, lidarr_filename, slskd_filename).ratio()
    return ratio


def best_filename_ratio(
    lidarr_filename: str, slskd_filename: str, lidarr_album_name: str, minimum_match_ratio: float
) -> float:
    ratio = difflib.SequenceMatcher(None, lidarr_filename, slskd_filename).ratio()
    for sep in (" ", "_", ""):
        ratio = check_ratio(sep, ratio, lidarr_filename, slskd_filename, minimum_match_ratio)
    ratio = check_ratio("", ratio, lidarr_album_name + " " + lidarr_filename, slskd_filename, minimum_match_ratio)
    ratio = check_ratio(" ", ratio, lidarr_album_name + " " + lidarr_filename, slskd_filename, minimum_match_ratio)
    ratio = check_ratio("_", ratio, lidarr_album_name + " " + lidarr_filename, slskd_filename, minimum_match_ratio)
    return ratio


def album_filename_analysis(lidarr_tracks, slskd_tracks, filetype: str, lidarr_album_name: str, minimum_match_ratio: float) -> dict:
    ext = filetype.split(" ")[0]
    matched = 0
    worst_ratio = 1.0
    worst_track = ""
    worst_peer_file = ""
    for lidarr_track in lidarr_tracks:
        lidarr_filename = lidarr_track["title"] + "." + ext
        best_match = 0.0
        best_peer = ""
        for slskd_track in slskd_tracks:
            ratio = best_filename_ratio(lidarr_filename, slskd_track["filename"], lidarr_album_name, minimum_match_ratio)
            if ratio > best_match:
                best_match = ratio
                best_peer = slskd_track["filename"]
        if best_match > minimum_match_ratio:
            matched += 1
        elif best_match < worst_ratio:
            worst_ratio = best_match
            worst_track = lidarr_track["title"]
            worst_peer_file = best_peer
    return {
        "matched": matched,
        "total": len(lidarr_tracks),
        "worst_ratio": worst_ratio if matched < len(lidarr_tracks) else 1.0,
        "worst_track": worst_track,
        "worst_peer_file": worst_peer_file,
    }


def release_diag_label(release: dict) -> str:
    country = release["country"][0] if release.get("country") else "?"
    return f"{release.get('trackCount', '?')}t {country} {release.get('format', '?')}"
