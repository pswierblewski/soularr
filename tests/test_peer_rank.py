from peer_rank import peer_upload_speed, rank_search_responses


def test_peer_upload_speed_missing_and_null_are_zero():
    assert peer_upload_speed({}) == 0
    assert peer_upload_speed({"uploadSpeed": None}) == 0
    assert peer_upload_speed({"uploadSpeed": "nope"}) == 0


def test_peer_upload_speed_parses_int():
    assert peer_upload_speed({"uploadSpeed": 130340}) == 130340
    assert peer_upload_speed({"uploadSpeed": "9910000"}) == 9910000


def test_rank_orders_by_upload_speed_descending():
    results = [
        {"username": "dazzbog", "uploadSpeed": 130340, "files": [1]},
        {"username": "caress", "uploadSpeed": 9910000, "files": [2]},
        {"username": "slowpoke", "uploadSpeed": None, "files": [3]},
    ]
    ranked = rank_search_responses(results)
    assert [r["username"] for r in ranked] == ["caress", "dazzbog", "slowpoke"]


def test_rank_keeps_max_speed_for_duplicate_username():
    results = [
        {"username": "caress", "uploadSpeed": 100, "files": ["a"]},
        {"username": "other", "uploadSpeed": 500, "files": ["b"]},
        {"username": "caress", "uploadSpeed": 9000, "files": ["c"]},
    ]
    ranked = rank_search_responses(results)
    assert [r["username"] for r in ranked] == ["caress", "other"]
    assert ranked[0]["files"] == ["c"]


def test_rank_stable_on_equal_speed():
    results = [
        {"username": "aaa", "uploadSpeed": 100, "files": [1]},
        {"username": "bbb", "uploadSpeed": 100, "files": [2]},
    ]
    ranked = rank_search_responses(results)
    assert [r["username"] for r in ranked] == ["aaa", "bbb"]
