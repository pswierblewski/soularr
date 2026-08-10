"""Rank slskd search responses by peer uploadSpeed (soularr fork)."""


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
