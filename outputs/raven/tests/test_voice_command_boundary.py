import pytest

from app.ai import conversational_shortcut
from app.assistant_jobs import parse_command
from app.main import normalize_voice_transcript, spotify_command, voice_ui_command


@pytest.mark.parametrize("heard", ["two career", "too research", "to knowledge"])
def test_navigation_destination_fragments_are_safe_actions(heard):
    assert voice_ui_command(heard)["type"] == "navigate"


def test_observed_tame_impala_asr_variants_are_repaired():
    assert normalize_voice_transcript("play loser by taminfala") == "play loser by Tame Impala"
    assert normalize_voice_transcript("play loser by tamin pala") == "play loser by Tame Impala"


def test_track_fragment_continues_a_play_request():
    assert spotify_command("Antidote by Migos", ["play"]) == {"mode": "play", "query": "Antidote by Migos"}


@pytest.mark.parametrize("text", ["for dog walking jobs in Atlanta", "generate a media post for me on a futuristic city", "generate a real visual on a futuristic city"])
def test_transcript_tool_requests_do_not_fall_through_to_dialogue(text):
    assert parse_command(text) is not None


@pytest.mark.parametrize("text", ["wait wait Raven", "interrupt", "hold on"])
def test_barge_in_language_is_zero_token_dialogue(text):
    assert conversational_shortcut(text) == "Okay—I’m listening."
