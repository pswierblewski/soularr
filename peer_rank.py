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
