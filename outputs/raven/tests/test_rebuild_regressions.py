import pytest
from app.main import voice_ui_command,spotify_command,youtube_command
from app.assistant_jobs import parse_command

@pytest.mark.parametrize('text',['play my likes songs','play my like songs','no i said i said no no i said play my liked songs','yeah i said play my liked songs'])
def test_library_not_random_track(text):
    assert spotify_command(text)['mode']=='liked_play'

@pytest.mark.parametrize('text',['go to capabilities','no i said go to capabilities i said go to capabilities'])
def test_capabilities(text):
    assert voice_ui_command(text)['page']=='tools'

def test_not_openrouter_navigation():
    assert voice_ui_command("ok it looks like the open router aspect didn't work either") is None

def test_zoom_again():
    assert voice_ui_command('zoom in again','graph')['type']=='graph_zoom'

@pytest.mark.parametrize('text',['open youtube for me with videos of cats','open youtube videos of cats','pull up the videos of cats on youtube for me'])
def test_cat_videos(text):
    assert youtube_command(text)=={'mode':'search_open','query':'cats'}

def test_discover_video():
    assert youtube_command('alright on youtube find videos of cats')=={'mode':'search','query':'cats'}

def test_research_status_not_start():
    assert parse_command('deep research queries')['action']=='status'

@pytest.mark.parametrize('text',['can you cancel the research',"no cancel cancel that research cancel that research job it's not what I meant"])
def test_research_cancel(text):
    assert parse_command(text)['action']=='cancel_research'
