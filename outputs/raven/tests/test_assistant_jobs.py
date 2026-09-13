import uuid
from unittest.mock import AsyncMock, patch
import pytest
from app.assistant_jobs import parse_command, execute, resolve_target, handle
from app.main import split_compound_commands

PREFIXES=['','Hey Raven, ','Raven, please ','Can you ','Could you please ','Okay, ']
TAILS=['',' in the background',' while we talk',' and tell me the results']
COMMANDS=[('Find sales jobs in Atlanta','career_search'),('Look for remote sales jobs','career_search'),('Run a job search for software engineers','career_search'),('Research local hiring trends','research'),('Start deep research on robot vacuums','research'),('Look into battery recycling','research'),('Create a content campaign about cats for Instagram','content'),('Generate posts about gardening for YouTube','content'),('Tailor my resume for job account executive at Example','career_tailor'),('Prepare an application for job abc','career_tailor'),('Apply for job abc','application_review'),('Submit approved application abc','application_execute'),('Generate media for post abc','media')]

@pytest.mark.parametrize('prefix',PREFIXES)
@pytest.mark.parametrize('tail',TAILS)
@pytest.mark.parametrize('text,action',COMMANDS)
def test_variations(prefix,tail,text,action):
    assert parse_command(prefix+text+tail)['action']==action

@pytest.mark.parametrize('text',['Can you do research?','I want to discuss research methods','Do you have a resume tool?','Do not apply for job abc','Publish everything','Submit application abc','Open Spotify','What is content generation?'])
def test_not_execution(text):assert parse_command(text) is None

@pytest.mark.parametrize('text',['How is my background task going?','What did my job search find?','Summarize my research results','What did my content task produce?','What did you find?','Is it done?'])
def test_followups(text):assert parse_command(text)['action']=='status'

@pytest.mark.parametrize('text,action',[('Find jobs in Atlanta','career_search'),('Find me jobs in Atlanta','career_search'),('Start an in-depth research agent on solar power','research'),('What did the research agent find?','status'),('Tailor my resume for the first job','career_tailor'),('Generate media for the second post','media')])
def test_natural_variants(text,action):assert parse_command(text)['action']==action

@pytest.mark.parametrize('join',[' and ',' then ',' and then ','; ','. ', ' after that '])
def test_cross_tool_chain(join):
    parts=split_compound_commands('Find sales jobs in Atlanta'+join+'research solar technology'+join+'create a content campaign about solar power')
    assert [parse_command(p)['action'] for p in parts]==['career_search','research','content']

@pytest.mark.asyncio
async def test_owner_scoped_ambiguous_target():
    uid=uuid.uuid4()
    pool=AsyncMock();pool.fetch.return_value=[{'id':uuid.uuid4()},{'id':uuid.uuid4()}]
    with patch('app.assistant_jobs.db.pool',pool):
        with pytest.raises(Exception,match='unique exact'):await resolve_target(uid,'career_tailor','Sales')
    assert pool.fetch.call_args.args[1]==uid

@pytest.mark.asyncio
async def test_career_calls_real_service_not_mission():
    uid=uuid.uuid4();job={'user_id':uid,'action':'career_search','payload':{'query':'sales jobs in Atlanta'}}
    service=AsyncMock(return_value={'search_id':str(uuid.uuid4()),'results':[{'title':'Sales','company':'Example','id':'saved'}]})
    with patch('app.assistant_jobs.current_user',AsyncMock(return_value=str(uid))),patch('app.main.search_career_jobs',service):
        result,status=await execute(job)
    assert status=='completed' and result['jobs'][0]['company']=='Example'
    assert service.call_args.args[0].location=='Atlanta'

@pytest.mark.asyncio
async def test_wrong_owner_cannot_execute():
    with patch('app.assistant_jobs.current_user',AsyncMock(return_value=str(uuid.uuid4()))):
        with pytest.raises(Exception,match='authorized'):await execute({'user_id':uuid.uuid4(),'action':'career_search','payload':{'query':'sales jobs'}})

@pytest.mark.asyncio
async def test_status_does_not_start_new_work():
    pool=AsyncMock();pool.fetchrow.return_value={'id':uuid.uuid4(),'action':'research','status':'waiting','result':{'summary':'Collecting evidence.'}}
    with patch('app.assistant_jobs.db.pool',pool),patch('app.assistant_jobs.enqueue',AsyncMock()) as queue:
        text,ids=await handle(uuid.uuid4(),uuid.uuid4(),parse_command('What did you find?'))
        queue.assert_not_called()
    assert 'waiting' in text and len(ids)==1

@pytest.mark.asyncio
@pytest.mark.parametrize('action,service,payload,expected',[('research','create_project',uuid.uuid4(),'waiting'),('media','generate_post_media',{'id':str(uuid.uuid4())},'waiting'),('application_execute','execute_application',{'status':'submitted','verification':{'confirmation_id':'test'}},'completed')])
async def test_typed_dispatch(action,service,payload,expected):
    uid=uuid.uuid4();job={'user_id':uid,'action':action,'payload':{'query':'test topic','target':str(uuid.uuid4())}}
    with patch('app.assistant_jobs.current_user',AsyncMock(return_value=str(uid))),patch('app.main.'+service,AsyncMock(return_value=payload)) as endpoint:
        result,status=await execute(job)
    assert status==expected and endpoint.await_count==1
    if action=='media':assert 'queued' in result['summary'] and 'ready' not in result['summary']

@pytest.mark.asyncio
async def test_application_prepare_does_not_execute():
    uid=uuid.uuid4();job={'user_id':uid,'action':'application_review','payload':{'query':'x','target':str(uuid.uuid4())}}
    result={'resume':{'id':'saved'},'application':{'id':str(uuid.uuid4())},'usage':{}}
    with patch('app.assistant_jobs.current_user',AsyncMock(return_value=str(uid))),patch('app.main.tailor_application',AsyncMock(return_value=result)) as tailor,patch('app.main.request_application_approval',AsyncMock(return_value={'id':uuid.uuid4()})) as approval,patch('app.main.execute_application',AsyncMock()) as submit:
        output,status=await execute(job)
    assert tailor.await_count==approval.await_count==1 and submit.await_count==0
    assert 'Nothing has been submitted' in output['summary']
