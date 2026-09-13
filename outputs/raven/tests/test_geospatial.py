import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError
from app import geospatial as g


@pytest.fixture(autouse=True)
def clear_world_cache():
    g._cache.clear();g._locks.clear();g._geo_cache.clear()
    yield
    g._cache.clear();g._locks.clear();g._geo_cache.clear()


@pytest.mark.parametrize('args',[{'action':'shell'},{'action':'fly_to','latitude':91},{'action':'fly_to','longitude':float('nan')},{'action':'set_layer','layer':'private_people'},{'action':'navigate','url':'http://127.0.0.1'}])
def test_action_rejects_unknown_or_unsafe_input(args):
    with pytest.raises(ValidationError):g.WorldAction(**args)


def test_context_is_bounded():
    with pytest.raises(ValidationError):g.WorldContext(visible_ids=['x']*41)
    with pytest.raises(ValidationError):g.WorldContext(viewport={'latitude':float('inf')})


@pytest.mark.asyncio
async def test_aircraft_excludes_stale_and_invalid_positions(monkeypatch):
    monkeypatch.setattr(g,'upstream',AsyncMock(return_value={'ac':[{'hex':'ok','lat':33.7,'lon':-84.3,'seen_pos':4,'flight':'TEST1','alt_baro':10000},{'hex':'old','lat':33,'lon':-84,'seen_pos':200},{'hex':'bad','lat':150,'lon':0,'seen_pos':2}]}))
    rows=await g.fetch_entities('aircraft',33,-84)
    assert len(rows)==1 and rows[0]['altitude']==3048
    assert rows[0]['metadata']['destination']=='Not supplied by this feed'


@pytest.mark.asyncio
async def test_quake_metadata_and_observed_time(monkeypatch):
    monkeypatch.setattr(g,'upstream',AsyncMock(return_value={'features':[{'id':'q','properties':{'mag':4.8,'place':'Japan','time':1700000000000,'url':'https://earthquake.usgs.gov/q'},'geometry':{'coordinates':[139,35,12]}}]}))
    rows=await g.fetch_entities('earthquakes',0,0)
    assert rows[0]['latitude']==35 and rows[0]['metadata']['depth_km']==12
    assert rows[0]['observed_at'].startswith('2023-11')


@pytest.mark.asyncio
async def test_cache_coalesces_and_failures_preserve_labeled_snapshot(monkeypatch):
    fetch=AsyncMock(return_value=[g.entity('aircraft','a','Flight',33,-84)])
    monkeypatch.setattr(g,'fetch_entities',fetch)
    a,b=await asyncio.gather(g.feed('aircraft'),g.feed('aircraft'))
    assert fetch.await_count==1 and b['freshness']=='cached'
    item=next(iter(g._cache.values()));item['retry_at']=0
    fetch.side_effect=RuntimeError('never show secrets from exceptions')
    failed=await g.feed('aircraft')
    assert failed['status']=='stale' and len(failed['entities'])==1
    assert 'secrets' not in failed['detail']


@pytest.mark.asyncio
async def test_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv('WORLD_AISSTREAM_API_KEY',raising=False)
    out=await g.feed('ships')
    assert out['status']=='api_key_required' and not out['entities']


@pytest.mark.asyncio
async def test_rate_limit_does_not_fake_live_data(monkeypatch):
    response=httpx.Response(429,request=httpx.Request('GET','https://public.example'))
    monkeypatch.setattr(g,'fetch_entities',AsyncMock(side_effect=httpx.HTTPStatusError('limited',request=response.request,response=response)))
    out=await g.feed('launches')
    assert out['status']=='rate_limited' and out['entities']==[]


def test_model_receives_only_canonical_enabled_visible_records():
    g._cache['earthquakes']={'at':time.monotonic(),'data':{'entities':[g.entity('earthquakes','real','Real event',35,139)],'ttl':120,'status':'available'}}
    c=g.WorldContext(layers=['earthquakes'],visible_ids=['earthquakes:real','earthquakes:fake'])
    assert [e['id'] for e in g.selected_evidence(c)]==['earthquakes:real']
    c.layers=[]
    assert not g.selected_evidence(c)


@pytest.mark.asyncio
async def test_research_handoff_creates_actual_job_and_save_is_explicit(monkeypatch):
    from app import main as m
    monkeypatch.setattr(g,'current_user',AsyncMock(return_value='00000000-0000-0000-0000-000000000001'))
    create=AsyncMock(return_value='00000000-0000-0000-0000-000000000002');save=AsyncMock()
    monkeypatch.setattr(m,'create_project',create);monkeypatch.setattr(m,'add_memory',save)
    out=await g.execute_actions([g.WorldAction(action='research')],g.WorldContext(viewport={'region':'Atlanta'}),SimpleNamespace(cookies={}))
    assert create.await_count==1 and save.await_count==0
    assert out['ui_action']['actions'][0]['action']=='research_queued'
    assert 'Atlanta' in create.call_args.args[2]


@pytest.mark.asyncio
async def test_unknown_destination_does_not_start_speculative_research(monkeypatch):
    from app import main as m
    monkeypatch.setattr(g,'current_user',AsyncMock(return_value='00000000-0000-0000-0000-000000000001'))
    create=AsyncMock();monkeypatch.setattr(m,'create_project',create)
    out=await g.execute_actions([g.WorldAction(action='research',location='the destination')],g.WorldContext(),SimpleNamespace(cookies={}))
    create.assert_not_called();assert 'Which place' in out['results'][0]


@pytest.mark.asyncio
async def test_compound_navigation_toggles_have_ordered_actions(monkeypatch):
    monkeypatch.setattr(g,'current_user',AsyncMock(return_value='00000000-0000-0000-0000-000000000001'))
    monkeypatch.setattr(g,'search_location',AsyncMock(return_value=[{'latitude':33.75,'longitude':-84.39,'name':'Atlanta, Georgia'}]))
    out=await g.execute_actions([g.WorldAction(action='navigate',location='Atlanta'),g.WorldAction(action='set_layer',layer='aircraft')],g.WorldContext(),SimpleNamespace(cookies={}))
    assert [a['action'] for a in out['ui_action']['actions']]==['fly_to','set_layer']
    assert out['context']['layers']==['aircraft']


@pytest.mark.asyncio
async def test_follow_unknown_entity_never_invents_target(monkeypatch):
    monkeypatch.setattr(g,'current_user',AsyncMock(return_value='00000000-0000-0000-0000-000000000001'))
    out=await g.execute_actions([g.WorldAction(action='follow_entity',entity_id='ghost')],g.WorldContext(),SimpleNamespace(cookies={}))
    assert out['ui_action']['actions']==[]
    assert 'Select a visible object' in out['results'][0]


def test_no_arbitrary_protocol_in_source_link():
    assert g.safe_url('javascript:alert(1)')==''
    assert g.safe_url('https://user:secret@example.com')==''
