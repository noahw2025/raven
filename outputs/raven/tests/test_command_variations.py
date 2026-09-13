import pytest
from app.main import split_compound_commands, spotify_command, discord_channel_command, desktop_app_command, desktop_close_command, youtube_command

PREFIXES=['','Raven, ','Hey Raven, ','Please ','Can you ','Could you please ','Okay, ','Raven, please ']
JOINS=[' and ',' then ',' and then ', ', then ', '; ', '. ', ', ', ' after that ', ' also ']

@pytest.mark.parametrize('prefix',PREFIXES)
@pytest.mark.parametrize('join',JOINS)
@pytest.mark.parametrize('title',['Good Morning by Kanye West','Whitsand Bay by Metronomy','Home by Edward Sharpe and the Magnetic Zeros'])
def test_spotify_variations(prefix,join,title):
    parts=split_compound_commands(prefix+'open Spotify'+join+'play '+title)
    assert len(parts)==2
    assert spotify_command(parts[0])=={'mode':'open','query':''}
    assert spotify_command(parts[1])=={'mode':'play','query':title}

@pytest.mark.parametrize('utterance',[
    'Hey Raven, can you open Spotify?',
    'Hey Raven can you open Spotify',
    'Raven, could you please open the Spotify app?',
    'Will you launch Spotify?',
    'Okay, Raven, open Spotify.',
    'Hi Raven, go ahead and open Spotify',
])
def test_polite_single_spotify_open_commands(utterance):
    assert spotify_command(utterance)=={'mode':'open','query':''}
    assert desktop_app_command(utterance)=='spotify'

def test_spotify_explanation_is_not_an_open_command():
    assert spotify_command('Can you explain how Spotify works?') is None
    assert desktop_app_command('Can you explain how Spotify works?') is None

@pytest.mark.parametrize('utterance',[
    'Close Spotify', 'Hey Raven, can you close Spotify?', 'Please quit the Spotify app',
    'Would you shut down Spotify?', 'Okay, Raven, exit Spotify', 'close spotofiy', 'close fight if I',
])
def test_natural_spotify_close_commands(utterance):
    assert desktop_close_command(utterance)=='spotify'

@pytest.mark.parametrize('prefix',PREFIXES)
@pytest.mark.parametrize('join',JOINS)
@pytest.mark.parametrize('tail',['join general','join general channel','join the general channel','join channel general','go to general channel'])
def test_discord_variations(prefix,join,tail):
    parts=split_compound_commands(prefix+'open Discord'+join+tail)
    assert len(parts)==2
    assert desktop_app_command(parts[0])=='discord'
    assert discord_channel_command(parts[1],parts[:1])=='general'

def test_quoted_titles_and_unknown_steps():
    assert len(split_compound_commands('Open Spotify and play "Stop and Play" by Example'))==2
    assert split_compound_commands('Open Spotify and run powershell')[1]=='run powershell'
    assert split_compound_commands('We could open Spotify and play a song')==[]
    assert discord_channel_command('join general') is None
    assert discord_channel_command('open YouTube',['open Discord']) is None

def test_mixed_chain():
    parts=split_compound_commands('Open Spotify and play Whitsand Bay by Metronomy then set volume to 35 percent and open Discord and join general channel then open YouTube with videos of cats')
    assert len(parts)==6
    assert spotify_command(parts[2])['mode']=='volume'
    assert discord_channel_command(parts[4],parts[:4])=='general'
    assert youtube_command(parts[5])=={'mode':'search_open','query':'cats'}
