"""Read-only projection of existing domain work; never a second job scheduler."""
import math

def semantic_fit(lexical,a,b):
    if len(a)!=len(b):raise ValueError('Embedding dimension mismatch')
    norm=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    similarity=max(0,min(1,sum(x*y for x,y in zip(a,b))/norm)) if norm else 0
    return round(.65*lexical+35*similarity),round(similarity,4)

def phase_group(status):
    if status in {'completed','submitted','published','media_ready','ready','done'}:return 'completed'
    if status in {'failed','error','rejected'}:return 'failed'
    if status in {'cancelled','archived'}:return 'archived'
    if status in {'waiting_approval','pending','needs_input','materials_ready','draft','brief_ready'}:return 'waiting'
    if status=='scheduled':return 'scheduled'
    return 'active'

def station_for(action):
    if 'research' in action:return 'research'
    if action.startswith(('career','application')):return 'career'
    if action in {'content','media','create_image','create_video'}:return 'studio'
    return 'missions'

def project_activity(research,jobs,assets,approvals,runs):
    items=[]
    for row in research:
        items.append(dict(id=str(row['id']),kind='research',workspace='research',title=row['title'],status=row['status'],stage=row['status'],detail=f"{row['source_count']} sources · {row['finding_count']} findings",error=row.get('error',''),updated_at=row['updated_at'],artifact=f"/api/research/projects/{row['id']}/download" if row['status']=='completed' else None))
    for row in jobs:
        # Research appears once, using its domain record rather than its queue wrapper.
        if row['action']=='research':continue
        result=row.get('result') or {}
        items.append(dict(id=str(row['id']),kind='assistant_job',workspace=station_for(row['action']),title=(row.get('payload') or {}).get('query') or row['action'],status=row['status'],stage=row['action'].replace('_',' '),detail=result.get('summary',''),error=result.get('error',''),updated_at=row['updated_at'],artifact=None))
    linked={str((j.get('result') or {}).get('asset_id')) for j in jobs}
    for row in assets:
        if str(row['id']) in linked:continue
        items.append(dict(id=str(row['id']),kind='media',workspace='studio',title=row['prompt'][:160] or 'Media generation',status=row['status'],stage=row['kind'],detail=row['provider'],error='',updated_at=row['created_at'],artifact=f"/api/social/assets/{row['id']}/content" if row['status']=='media_ready' else None))
    for row in approvals:
        items.append(dict(id=str(row['id']),kind='approval',workspace='trust',title='Decision required',status='waiting_approval',stage='Owner approval',detail='Review the exact target and proposed action in Approvals.',error='',updated_at=row['created_at'],artifact=None))
    for row in runs:
        items.append(dict(id=str(row['id']),kind='mission',workspace='missions',title=row['title'],status=row['status'],stage='Mission',detail='',error='',updated_at=row['updated_at'],artifact=None))
    for item in items:item['group']=phase_group(item['status'])
    return sorted(items,key=lambda x:str(x['updated_at']),reverse=True)
