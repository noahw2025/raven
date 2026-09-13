import asyncio
import pytest
from app.main import voice_ui_command
from app.assistant_jobs import parse_command,handle
from app.ai import AI
from app.config import Settings
from app.career_discovery import is_job_detail_url,actionable_job

@pytest.mark.parametrize('url',['https://jobs.lever.co/spotify','https://linkedin.com/jobs/sales-jobs-atlanta','https://merriam-webster.com/dictionary/account','https://linkedin.com.attacker.test/jobs/view/123'])
def test_non_job_results_rejected(url):
    assert not is_job_detail_url(url)
    assert not actionable_job({'source_provider':'public_web_index','source_url':url})

def test_specific_job_link_accepted():
    assert is_job_detail_url('https://boards.greenhouse.io/example/jobs/123456')

@pytest.mark.parametrize('text',["'kay actually take me to knowledge","actually take me to knowledge","go to knowledge tab"])
def test_knowledge_navigation(text):
    assert voice_ui_command(text,'research')['page']=='graph'

def test_camera_not_memory_search():
    assert voice_ui_command('zoom in on the knowledge graph','graph')=={'type':'graph_zoom','direction':'in','label':'Knowledge Graph'}

def test_asr_find_memories():
    action=voice_ui_command('okay fine memories on spotify','graph')
    assert action['type']=='graph_filter' and action['query']=='spotify'

def test_no_quoted_execution():
    assert voice_ui_command('the transcript has an issue if I say go to knowledge tab','research') is None

def test_work_and_hermes():
    assert voice_ui_command('go to work')['page']=='missions'
    assert voice_ui_command('open Hermes tools')['page']=='hermes'
    assert parse_command('Ask Hermes to research cats')['action']=='research'

def test_new_transcript_regressions():
    assert voice_ui_command('Can you select memories for me, please','graph')['object_type']=='memory'
    assert voice_ui_command('pull me all memories of video game titles','graph')['query']=='video game titles'
    assert voice_ui_command('i said go to content','graph')['page']=='studio'
    assert voice_ui_command('speak slower')['type']=='voice_rate'
    assert parse_command('okay fine me jobs for marketing positions in atlanta')['action']=='career_search'
    assert parse_command('generate an image of a futuristic city')['action']=='create_image'
    assert parse_command('generate a video of clouds')['action']=='create_video'

def test_incomplete_topic_does_not_enqueue():
    cmd=parse_command("okay run a deep research on let's make it on")
    assert cmd['action']=='clarify_research'
    answer,ids=asyncio.run(handle(None,None,cmd))
    assert 'What topic' in answer and not ids

def test_openrouter_missing_key_never_falls_back():
    ai=AI(Settings(raven_admin_password='test',raven_jwt_secret='x'*32,raven_research_provider='openrouter',openrouter_api_key=''))
    async def forbidden(*args,**kwargs):raise AssertionError('Local model must not run')
    ai.structured=forbidden
    with pytest.raises(RuntimeError,match='server-side API key'):
        asyncio.run(ai.research_structured('Research','cats'))

def test_paid_route_rejected():
    ai=AI(Settings(raven_admin_password='test',raven_jwt_secret='x'*32,openrouter_api_key='fake-test-value',openrouter_model='paid/model',raven_research_provider='openrouter'))
    with pytest.raises(RuntimeError,match='only permits free'):
        asyncio.run(ai.research_structured('Research','cats'))
