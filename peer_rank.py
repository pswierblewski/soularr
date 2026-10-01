"""Rank slskd search responses by peer uploadSpeed (soularr fork)."""

from collections import Counter


def peer_upload_speed(result: dict) -> int:
    speed = result.get("uploadSpeed")
    if speed is None:
        return 0
    try:
        return int(speed)
    except (TypeError, ValueError):
        return 0


def rank_search_responses(search_results: list) -> list:
    """
    Collapse duplicate usernames (keep max uploadSpeed response),
    then sort by uploadSpeed descending. Equal speeds keep first-seen order.
    """
    best_by_user = {}
    first_index = {}
    for index, result in enumerate(search_results):
        username = result["username"]
        speed = peer_upload_speed(result)
        if username not in first_index:
            first_index[username] = index
            best_by_user[username] = result
            continue
        if speed > peer_upload_speed(best_by_user[username]):
            best_by_user[username] = result

    return sorted(
        best_by_user.values(),
        key=lambda result: (
            -peer_upload_speed(result),
            first_index[result["username"]],
        ),
    )


def fill_search_cache(
    search_cache: dict,
    album_id,
    ranked_results: list,
    allowed_filetypes,
    verify_filetype,
) -> None:
    """Merge ranked search results into an album's per-user directory cache."""
    if album_id not in search_cache:
        search_cache[album_id] = {}

    album_cache = search_cache[album_id]
    for result in ranked_results:
        username = result["username"]
        if username not in album_cache:
            album_cache[username] = {}
        for file in result["files"]:
            file_dir = file["filename"].rsplit("\\", 1)[0]
            for allowed_filetype in allowed_filetypes:
                if verify_filetype(file, allowed_filetype):
                    if allowed_filetype not in album_cache[username]:
                        album_cache[username][allowed_filetype] = []
                    if file_dir not in album_cache[username][allowed_filetype]:
                        album_cache[username][allowed_filetype].append(file_dir)


def peer_folder_audio_counts(ranked_results: list, allowed_filetypes: list, verify_filetype) -> list[tuple[int, int]]:
    """
    Histogram of audio file counts per folder as seen in search snippets.
    Returns [(track_count, folder_hits), ...] sorted by folder_hits descending.
    """
    histogram: Counter[int] = Counter()
    for result in ranked_results:
        per_dir: dict[str, int] = {}
        for file in result.get("files", []):
            for allowed_filetype in allowed_filetypes:
                if not verify_filetype(file, allowed_filetype):
                    continue
                file_dir = file["filename"].rsplit("\\", 1)[0]
                per_dir[file_dir] = per_dir.get(file_dir, 0) + 1
        for count in per_dir.values():
            histogram[count] += 1
    return histogram.most_common()


def sort_releases_by_peer_track_count(releases: list, peer_histogram: list[tuple[int, int]]) -> list:
    """Order releases so track counts matching Soulseek folders are tried first."""
    if not peer_histogram or not releases:
        return releases
    preferred = peer_histogram[0][0]

    def sort_key(release: dict) -> tuple:
        track_count = release.get("trackCount") or 0
        return (abs(track_count - preferred), -track_count)

    return sorted(releases, key=sort_key)
