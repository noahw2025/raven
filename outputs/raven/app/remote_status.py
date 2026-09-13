"""Public-safe readiness projection; credentials never leave the server."""
import httpx

async def status(settings):
    result={"connected":False,"reasoner_ready":False,"tools":[],"model":settings.openrouter_model,"openrouter_configured":bool(settings.openrouter_api_key),"research_provider":settings.raven_research_provider,"content_provider":settings.content_text_provider}
    if not settings.hermes_url or not settings.hermes_token:
        return {**result,"detail":"Hermes worker is not configured."}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response=await client.get(settings.hermes_url.rstrip('/')+'/tools',headers={'Authorization':'Bearer '+settings.hermes_token})
        response.raise_for_status();body=response.json()
        result.update(model=body.get('model',result['model']),skills=[{key:str(item.get(key,''))[:600] for key in ('name','description','status','group')} for item in body.get('skills',[])],mcp=[{key:item.get(key,'') for key in ('name','url','status','auth_configured')} for item in body.get('mcp',[])],mcp_status=body.get('mcp_status','Inventory unavailable'),enabled_toolsets=body.get('enabled_toolsets',[]),toolsets=[{key:item.get(key,'') for key in ('name','description','enabled','tool_count')} for item in body.get('toolsets',[])])
        result.update(connected=True,reasoner_ready=bool(body.get('reasoner_ready')),tools=[{key:item.get(key,'') for key in ('name','description','status')} for item in body.get('tools',[])],detail=body.get('restriction','Research-only worker'))
    except (httpx.HTTPError,ValueError,TypeError):result['detail']='Hermes worker is unavailable. No tools were claimed ready.'
    return result
