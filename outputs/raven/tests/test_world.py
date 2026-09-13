from datetime import datetime,timezone
from app.world import phase_group,project_activity,semantic_fit
from app.main import voice_ui_command

def test_activity_is_real_and_research_not_duplicated():
    now=datetime.now(timezone.utc)
    research=[dict(id='r',title='Research example',status='searching',source_count=2,finding_count=0,updated_at=now)]
    jobs=[dict(id='j',action='research',result={},status='waiting',updated_at=now)]
    items=project_activity(research,jobs,[],[],[])
    assert len(items)==1 and items[0]['stage']=='searching' and items[0]['group']=='active'
    assert items[0]['artifact'] is None

def test_terminal_groups():
    assert phase_group('draft')=='waiting'
    assert phase_group('brief_ready')=='waiting'
    assert phase_group('cancelled')=='archived'
    assert phase_group('failed')=='failed'
    assert phase_group('waiting_approval')=='waiting'
    assert phase_group('media_ready')=='completed'

def test_semantic_fit_preserves_lexical_evidence_and_uses_cosine():
    assert semantic_fit(100,[1,0],[1,0])==(100,1)
    assert semantic_fit(100,[1,0],[0,1])==(65,0)
    assert semantic_fit(0,[1,0],[1,0])==(35,1)
    assert semantic_fit(0,[0,0],[1,0])==(0,0)
    import pytest
    with pytest.raises(ValueError):
        semantic_fit(50,[1],[1,0])

def test_memory_intent_across_pages():
    for page in ['command','talk','studio','graph']:
        a=voice_ui_command('Raven, only show memories about Spotify',page)
        assert a['type']=='graph_filter' and a['query']=='spotify'
        assert voice_ui_command('Show only Spotify memories',page)['query']=='spotify'
