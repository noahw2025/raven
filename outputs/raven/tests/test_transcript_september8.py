import asyncio
from unittest.mock import AsyncMock
import pytest
from app.main import voice_ui_command,desktop_app_command,spotify_command,youtube_command,split_compound_commands
from app.assistant_jobs import parse_command
from app.ai import AI,AIResult
from app.config import Settings

@pytest.mark.parametrize('text',[
 'find me jobs','can you find me jobs','no use the career center to find me jobs',
 'well no you gotta help me find jobs'])
def test_unspecified_career_clarifies(text):
    assert parse_command(text)['action']=='clarify_career'

@pytest.mark.parametrize('text',['give me jobs on ai consulting','find AI consulting jobs','search for remote consultant jobs'])
def test_career_action(text):
    assert parse_command(text)['action']=='career_search'

def test_specific_research_status():
    assert parse_command("what's going on with the egyptian cat research that we talked about before is it still running")['action']=='status'
    assert parse_command("okay go back to research what stop date on that")['navigate']=='research'

def test_graph_fragment_does_not_search_for_me():
    assert voice_ui_command('show me','graph')['type']=='clarify'
    assert voice_ui_command('only show me memories about steam','graph')['query']=='steam'
    assert voice_ui_command('go to go to career')['page']=='career'

@pytest.mark.parametrize('app',['Spotify','Discord','Steam','Apex Legends','Chrome','ChatGPT'])
@pytest.mark.parametrize('prefix',['open ','can you open ','go ahead and open '])
def test_app_variations(app,prefix):
    assert desktop_app_command(prefix+app)

def test_quoted_desire_is_not_execution():
    assert desktop_app_command("well i think i'll give codex a prompt for your ability to open spotify") is None

def test_multistep_and_youtube_title():
    assert len(split_compound_commands('open Spotify then play Good Morning by Kanye West'))==2
    assert youtube_command('open youtube for me with videos of Egyptian cats')['query']=='Egyptian cats'
    assert spotify_command('play my liked songs on shuffle')['mode']=='liked_shuffle'

def test_research_remote_failure_forces_local_not_content_remote(monkeypatch):
    remote=AsyncMock(side_effect=RuntimeError('truncated'))
    local=AsyncMock(return_value=({'report_markdown':'grounded test'},AIResult('test',10,5,0)))
    monkeypatch.setattr(AI,'_openrouter_structured',remote)
    async def checked(self,*args,**kwargs):
        assert self.s.ai_provider=='ollama'
        assert self.s.content_text_provider=='local'
        return await local(*args,**kwargs)
    monkeypatch.setattr(AI,'structured',checked)
    a=AI(Settings(raven_research_provider='openrouter',content_text_provider='openrouter'))
    result,usage=asyncio.run(a.research_structured('test','public fixture',500))
    assert 'fallback' in usage.provider and result['report_markdown']
    assert remote.await_count==local.await_count==1

def test_research_uses_nvidia_before_local_fallback(monkeypatch):
    remote=AsyncMock(side_effect=RuntimeError('truncated'))
    nvidia=AsyncMock(return_value=({'report_markdown':'nvidia report'},AIResult('test',20,10,0,'NVIDIA NIM','fixture')))
    local=AsyncMock(side_effect=AssertionError('local must not run when NVIDIA succeeds'))
    monkeypatch.setattr(AI,'_openrouter_structured',remote)
    monkeypatch.setattr(AI,'_nvidia_structured',nvidia)
    monkeypatch.setattr(AI,'structured',local)
    a=AI(Settings(raven_research_provider='openrouter',openrouter_api_key='server-only',nvidia_api_key='server-only'))
    result,usage=asyncio.run(a.research_structured('test','public fixture',500))
    assert result['report_markdown']=='nvidia report' and usage.provider=='NVIDIA NIM'
    assert remote.await_count==nvidia.await_count==1 and local.await_count==0

def test_research_nvidia_failure_reaches_local(monkeypatch):
    remote=AsyncMock(side_effect=RuntimeError('truncated'))
    nvidia=AsyncMock(side_effect=RuntimeError('rate limited'))
    local=AsyncMock(return_value=({'report_markdown':'local report'},AIResult('test',12,6,0)))
    monkeypatch.setattr(AI,'_openrouter_structured',remote)
    monkeypatch.setattr(AI,'_nvidia_structured',nvidia)
    async def checked(self,*args,**kwargs):return await local(*args,**kwargs)
    monkeypatch.setattr(AI,'structured',checked)
    a=AI(Settings(raven_research_provider='openrouter',openrouter_api_key='server-only',nvidia_api_key='server-only'))
    result,usage=asyncio.run(a.research_structured('test','public fixture',500))
    assert result['report_markdown']=='local report' and 'fallback' in usage.provider
    assert remote.await_count==nvidia.await_count==local.await_count==1
