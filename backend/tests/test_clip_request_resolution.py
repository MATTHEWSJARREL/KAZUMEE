from backend.commands.executor import resolve_clip_requester


def test_streamer_trigger_defaults_to_streamer_clip_status():
    requester_type, requester_id, requester_name = resolve_clip_requester({"role": "streamer"})
    assert requester_type == "streamer"
    assert requester_id is None
    assert requester_name == "Anonymous"


def test_viewer_payload_keeps_viewer_requester():
    requester_type, requester_id, requester_name = resolve_clip_requester({"requester_type": "viewer", "requester_id": "u1", "requester_name": "Ada"})
    assert requester_type == "viewer"
    assert requester_id == "u1"
    assert requester_name == "Ada"
