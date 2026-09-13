import os
from pathlib import Path
os.environ.setdefault("RAVEN_ADMIN_PASSWORD","test-password")
os.environ.setdefault("RAVEN_JWT_SECRET","x"*32)
from app.ai import chunks, conversational_intent, conversational_shortcut, digest, verified_tool_answer
from app.auth import issue, valid_password
from app.content import clean_hashtags, is_public_media_url, normalize_plan
from app.career import normalize_application_package, package_checksum, safe_filename
from app.career_discovery import fingerprint, matches, normalize, score_job
from app.resume_render import render_docx, render_pdf
from app.research import compact_subject, diverse_candidates, evidence_card, normalize_plan as normalize_research_plan, normalize_synthesis, official_query, report_quality, source_quality
from app.main import deep_research_command, desktop_app_command, desktop_close_command, discord_channel_command, login_failures, login_rate_state, mission_command, normalize_voice_transcript, spotify_command, split_compound_commands, unresolved_action_request, voice_ui_command, youtube_command
from app.capabilities import detail_for
from app.workflows import TEMPLATES, json_object
from app.config import get_settings
import jwt


def test_chunks_are_bounded_and_overlap():
    source = "Sentence one. " * 300
    result = chunks(source, size=200, overlap=30)
    assert len(result) > 2
    assert all(0 < len(x) <= 200 for x in result)


def test_digest_is_stable_and_not_raw_data():
    assert digest(b"secret") == digest(b"secret")
    assert digest(b"secret") != digest(b"other")
    assert "secret" not in digest(b"secret")


def test_password_comparison_and_session_claim():
    settings=get_settings()
    assert valid_password(settings.raven_admin_password)
    assert not valid_password("wrong")
    token = issue("owner-id")
    assert jwt.decode(token,settings.raven_jwt_secret,algorithms=["HS256"])["sub"] == "owner-id"


def test_workflow_templates_gate_consequential_tools():
    consequential={"social","brokerage","hermes"}
    for steps in TEMPLATES.values():
        for _,tool,approval_required in steps:
            if tool in consequential:
                assert approval_required


def test_json_records_survive_legacy_double_encoding():
    record={"summary":"durable result","cost":0.01}
    import json
    assert json_object(json.dumps(json.dumps(record))) == record


def test_conversation_router_resets_corrected_topics_and_resolves_followups():
    assert conversational_intent("I asked for the weather in Atlanta tomorrow",["Google stock price"])[0] == "weather"
    intent,query=conversational_intent("for me in Atlanta",["what is the weather tomorrow?"])
    assert intent == "weather" and "weather" in query
    assert conversational_intent("for me in Atlanta",["Google stock price"])[0] == "conversation"
    assert conversational_intent("What is today's date?",[])[0] == "temporal"
    assert conversational_intent("Are you searching the web right now?",[])[0] == "provenance"
    assert conversational_intent("Do publicly available research on Instagram publishing requirements",[])[0] == "deep_research"
    assert conversational_intent("Can you do deep research through the web for me?",[])[0] == "conversation"
    assert conversational_intent("Is that from the deep research agent though?",[])[0] == "conversation"


def test_conversation_shortcuts_are_natural_and_do_not_hallucinate():
    assert "doing well" in conversational_shortcut("Hey Raven, how are you today?")
    assert conversational_shortcut("Yeah, I mean...") == "Go ahead—I'm listening."


def test_verified_tool_renderer_preserves_numeric_facts():
    market="[Q1] GOOGL observed quote: 354.30 USD; exchange=NMS; observed_at=2026-08-07T20:00:00+00:00; feed_url=x"
    assert "$354.30 USD" in verified_tool_answer("market",market,"Google stock")
    weather="[Q1] Verified weather forecast for Atlanta, Georgia, US: date=2026-08-10 local timezone=America/New_York; conditions=partly cloudy; high=82°F; low=69°F; maximum precipitation probability=20%;"
    answer=verified_tool_answer("weather",weather,"weather in Atlanta tomorrow")
    assert "Tomorrow in Atlanta" in answer and "82°F" in answer and "20%" in answer


def test_content_plan_normalization_is_bounded_and_publishable():
    plan=normalize_plan({"posts":[{"title":"A","caption":"Useful post","hashtags":["#Local_AI","local-ai","Local_AI"],"asset_prompt":"Neon desk","format":"image"}]},3)
    assert plan == [{"title":"A","caption":"Useful post","hashtags":["Local_AI","localai"],"asset_prompt":"Neon desk","format":"image","rationale":""}]
    assert clean_hashtags("#one, two #one") == ["one","two"]


def test_instagram_media_url_requires_public_https():
    assert is_public_media_url("https://cdn.example.com/post.png")
    assert not is_public_media_url("http://cdn.example.com/post.png")
    assert not is_public_media_url("https://localhost/post.png")
    assert not is_public_media_url("https://127.0.0.1/post.png")


def test_career_package_is_bounded_and_version_checksum_is_stable():
    package=normalize_application_package({"resume_markdown":"# Noah\n"+"Experience "*20,"cover_letter":"Hello","match_score":140,"strengths":["Sales","sales"],"gaps":["AWS"],"answers":[{"question":"Why us?","answer":"Mission fit","basis":"resume"},{"question":"","answer":"ignored"}]})
    assert package["match_score"] == 100
    assert package["strengths"] == ["Sales"]
    assert package["answers"] == [{"question":"Why us?","answer":"Mission fit","basis":"resume"}]
    assert package_checksum(package["resume_markdown"],package["cover_letter"],package["answers"]) == package_checksum(package["resume_markdown"],package["cover_letter"],package["answers"])
    assert safe_filename("Acme / Account Executive resume.md") == "Acme-Account-Executive-resume.md"


def test_research_plan_and_findings_are_bounded():
    plan=normalize_research_plan({"queries":[{"query":"official requirements","rationale":"primary"},"counter evidence"],"sections":["Current state"]},"objective",1)
    assert len(plan["queries"]) == 2 and plan["queries"][0]["rationale"] == "primary"
    result=normalize_synthesis({"report_markdown":"Evidence [S1]","findings":[{"claim":"Supported","confidence":2,"source_indexes":[1,"2",0]}]})
    assert result["findings"][0]["confidence"] == 1
    assert result["findings"][0]["source_indexes"] == [1,2]


def test_research_source_tiers_prefer_primary_evidence_explainably():
    assert source_quality("www.nist.gov") == "institutional_primary"
    assert source_quality("github.com") == "technical_primary"
    assert source_quality("reuters.com") == "reputable_secondary"
    assert source_quality("random-blog.example") == "web_source"


def test_research_evidence_is_fact_dense_and_domain_diverse():
    page="Sign in. Privacy policy. Instagram accounts must use a professional account. Publishing supports 50 posts per day. Subscribe now."
    card=evidence_card(page,"Instagram publishing account requirements and limits")
    assert "professional account" in card and "50 posts" in card and "Privacy policy" not in card
    items=[{"url":f"https://docs.example.com/{i}","quality":"technical_primary"} for i in range(5)]+[{"url":"https://nist.gov/a","quality":"institutional_primary"}]
    selected=diverse_candidates(items,6)
    assert sum("docs.example.com" in x["url"] for x in selected)==3 and any("nist.gov" in x["url"] for x in selected)


def test_research_objectives_become_focused_authoritative_queries():
    objective="Research current official Instagram API content publishing requirements including account eligibility supported media authentication permissions limits and implementation architecture"
    subject=compact_subject(objective)
    assert subject.startswith("Instagram API content publishing") and "Research" not in subject
    assert official_query(subject).startswith("site:developers.facebook.com/")


def test_research_quality_gate_rejects_link_dumps_and_accepts_organized_answers():
    bad="# Sources\n"+"- [S1] link\n"*100+"Extractive fallback; follow the [S#] links."
    assert not report_quality(bad,[{"claim":"x"}]*5,8,2)[0]
    good="# Answer\nDirect conclusion [S1].\n## Key findings\n"+("Detailed grounded explanation [S2] [S3]. "*45)+"\n## Current developments\nDated facts [S4].\n## Risks\nKnown limits.\n## Recommendation\nAction."
    passed,detail=report_quality(good,[{"claim":"x"}]*5,8,2)
    assert passed and detail["score"]==1


def test_navigation_requires_an_explicit_command_shape():
    assert voice_ui_command("Open the tools and integrations")["page"] == "tools"
    assert voice_ui_command("Hey, take me to the research center.")["page"] == "research"
    assert voice_ui_command("Hey Raven, let's move to the content page")["page"] == "studio"
    assert voice_ui_command("Let's look into our memories")["page"] == "memory"
    assert voice_ui_command("Could you switch to the knowledge page?")["page"] == "graph"
    assert voice_ui_command("Go to knowledge.")["page"] == "graph"
    assert voice_ui_command("Okay, amazing. Now can you go to knowledge?")["page"] == "graph"
    assert voice_ui_command("Okay, I really appreciate that actually let's go into the knowledge and graph, okay?")["page"] == "graph"
    assert voice_ui_command("You didn't move to the knowledge and graph section.")["page"] == "graph"
    assert voice_ui_command("Zoom in here","graph") == {"type":"graph_zoom","direction":"in","label":"Knowledge Graph"}
    assert voice_ui_command("Zoom out here","studio")["type"] == "clarify"
    assert voice_ui_command("We'll work on getting you connected to that tooling") is None
    assert voice_ui_command("Could you go to where we are on?") is None


def test_desktop_control_is_a_fixed_allowlist_not_a_shell():
    assert desktop_app_command("Raven, launch Apex Legends") == "apex"
    assert desktop_app_command("open Chrome") == "chrome"
    assert desktop_app_command("open powershell and delete files") is None
    assert desktop_app_command("run C:\\anything.exe") is None
    assert desktop_app_command("open Spotify") == "spotify"
    assert desktop_app_command("open ChatGPT") == "chatgpt"
    assert desktop_app_command("It's not playing, open Steam") == "steam"
    assert desktop_app_command("Alright, let's get some music playing open Spotify") == "spotify"
    assert desktop_app_command("Yeah, I want to listen to music. Can you open Spotify, please?") == "spotify"
    assert desktop_close_command("Hey Raven, can you close Spotify?") == "spotify"
    assert desktop_close_command("close fight if I") == "spotify"
    assert desktop_close_command("Blows Spotify") == "spotify"
    assert desktop_close_command("Clothes, Spotify. Clothes, Spotify.") == "spotify"
    assert desktop_close_command("No clothes spotify") == "spotify"
    assert desktop_close_command("Thank you, Raven. I really appreciate that. Here's what I'm gonna have you do. Can you close Spotify?") == "spotify"
    assert desktop_close_command("Please quit Discord") == "discord"
    assert desktop_close_command("Shut down Apex Legends") == "apex"
    assert desktop_close_command("What happens if I close Spotify?") is None


def test_observed_voice_transcription_errors_are_narrowly_repaired():
    variants={
        "Can you open the score?":"open Spotify",
        "Brooklyn Spotify":"open Spotify",
        "Open spot if I":"open Spotify",
        "Clothes, Spotify. Clothes, Spotify.":"close Spotify",
        "Raven. Open Spotify and play Good Morning by Can I West.":"Raven, Open Spotify and play Good Morning by Kanye West.",
        "Play Loser by Taimin Paula":"Play Loser by Tame Impala",
        "play loser by tayman paula":"play loser by Tame Impala",
        "awesome go ahead and play loser by tamman paula":"awesome go ahead and play loser by Tame Impala",
        "play my like songs":"play my liked songs",
    }
    for heard,normalized in variants.items():
        assert normalize_voice_transcript(heard)==normalized
        assert spotify_command(normalized) or desktop_close_command(normalized) or split_compound_commands(normalized)
    assert normalize_voice_transcript("Play Brooklyn Spotify playlist") == "Play Brooklyn Spotify playlist"
    assert normalize_voice_transcript("Tell me about the score") == "Tell me about the score"


def test_media_commands_distinguish_launch_search_and_confirmed_play_intent():
    assert spotify_command('no whitesand beach',['play Good Morning']) == {'mode':'play','query':'whitesand beach'}
    assert spotify_command('whitesand bay',['play Good Morning','no whitesand beach']) == {'mode':'play','query':'whitesand bay'}
    assert spotify_command('play witesand beach now in my liked songs')['mode'] == 'library_search'
    assert spotify_command('play my liked songs') == {'mode':'liked_play','query':''}
    assert spotify_command('play my liked songs on spotify') == {'mode':'liked_play','query':''}
    assert spotify_command('play my liked songs on shuffle') == {'mode':'liked_shuffle','query':''}
    assert spotify_command('shuffle my saved music') == {'mode':'liked_shuffle','query':''}
    assert spotify_command('play Loser by Tame Impala from my liked songs') == {'mode':'library_search','query':'Loser by Tame Impala'}
    assert spotify_command("open Spotify") == {"mode":"open","query":""}
    assert spotify_command("OpenSpotify!") == {"mode":"open","query":""}
    assert spotify_command("play Midnight City by M83 on Spotify") == {"mode":"play","query":"Midnight City by M83"}
    assert spotify_command("Yeah, play Good Morning by Kanye West") == {"mode":"play","query":"Good Morning by Kanye West"}
    assert spotify_command("Okay. Play Loser by Tame Impala.") == {"mode":"play","query":"Loser by Tame Impala"}
    assert spotify_command("Yes, play it.",["Open Spotify","Loser by Tame Impala."]) == {"mode":"play","query":"Loser by Tame Impala"}
    assert spotify_command("Hey Raven pause Spotify music") == {"mode":"pause","query":""}
    assert spotify_command("pause this on") == {"mode":"pause","query":""}
    assert spotify_command("So pause on.") == {"mode":"pause","query":""}
    assert spotify_command("No, it didn't pause the song") == {"mode":"pause_correction","query":""}
    assert spotify_command("Backtrack one song skip backwards") == {"mode":"previous","query":""}
    assert spotify_command("Play",["Open Spotify"]) == {"mode":"resume","query":""}
    assert spotify_command("Turn it down",["Open Spotify","Play a song"]) == {"mode":"volume_relative","query":"","delta":-15}
    assert spotify_command("Turn it down to clicks",["Open Spotify","Play a song"]) == {"mode":"volume_clarify","query":"","heard":"clicks"}
    assert spotify_command("No, it didn't but that's okay. Hey, uh, go ahead pause the song",["Play loser by Tame Impala","Turn it down to clicks"]) == {"mode":"pause","query":""}
    assert spotify_command("Awesome!",["Play loser by Tame Impala","No, it didn't but that's okay. Hey, uh, go ahead pause the song"]) is None
    assert spotify_command("No why did you play that what the heck",["Play loser by Tame Impala"]) == {"mode":"playback_correction","query":"loser by Tame Impala"}
    assert spotify_command("No clothes spotify",["Play loser by Tame Impala"]) is None
    assert spotify_command("Spotify is open. Play this on.",["Play Good Morning by Kanye West"]) == {"mode":"play","query":"Good Morning by Kanye West"}
    assert spotify_command("No, it is not playing.",["Play Good Morning by Kanye West"]) == {"mode":"playback_correction","query":"Good Morning by Kanye West"}
    assert spotify_command("search Spotify for focus music") == {"mode":"search","query":"focus music"}
    assert spotify_command("Spotify is useful") is None
    assert discord_channel_command("join Discord channel general") == "general"
    assert discord_channel_command("open gaming on Discord") == "gaming"
    assert discord_channel_command("open Discord") is None
    assert unresolved_action_request("Can you shuffle Spotify somehow?") is not None
    assert unresolved_action_request("Turn it down to clicks",["Open Spotify","Play a song"]) is not None


def test_voice_graph_controls_are_real_ui_actions():
    assert voice_ui_command('rotate the graph left','graph') == {'type':'graph_control','direction':'left','label':'Knowledge Graph'}
    assert voice_ui_command('move the map up a little','graph') == {'type':'graph_control','direction':'up','label':'Knowledge Graph'}
    assert voice_ui_command('zoom in on the graph','graph') == {'type':'graph_zoom','direction':'in','label':'Knowledge Graph'}
    assert voice_ui_command('rotate the graph right','talk')['type'] == 'clarify'
    assert voice_ui_command('Zoom in on the open Spotify node please','graph') == {'type':'graph_filter','query':'spotify','object_type':'','zoom':True,'label':'Knowledge Graph'}
    assert voice_ui_command('Can you select memories for me, please','graph')['object_type'] == 'memory'
    assert voice_ui_command('Open and show me all the memories that include Spotify on them','graph')['query'].lower() == 'spotify'
    assert voice_ui_command('Only display goal memories','graph')['object_type'] == 'goal'
    assert voice_ui_command('What do you know about Spotify in our memory base','graph')['query'].lower() == 'spotify'


def test_spotify_device_activation_language_stays_truthful():
    source=Path(__file__).parents[1].joinpath("app","main.py").read_text(encoding="utf-8")
    assert 'params={"device_id":target["id"]}' in source
    assert "account reports no available playback device" in source


def test_youtube_voice_commands_are_explicit_and_bounded():
    assert youtube_command("Raven, open YouTube") == {"mode":"open","query":""}
    assert youtube_command("Okay, open YouTube") == {"mode":"open","query":""}
    assert youtube_command("Hey Raven, can you open YouTube for me with videos of cats?") == {"mode":"search_open","query":"cats"}
    assert youtube_command("YouTube did not open",["open YouTube"]) == {"mode":"open","query":""}
    assert youtube_command("YouTube did not open with videos of cats") == {"mode":"search_open","query":"cats"}
    assert youtube_command("Raven find a video on local AI agents on YouTube") == {"mode":"search","query":"local AI agents"}
    assert youtube_command("Raven, give me options of videos on resume automation") == {"mode":"search","query":"resume automation"}
    assert youtube_command("I mentioned YouTube yesterday") is None
    assert desktop_app_command("open youtube") is None


def test_compound_voice_commands_split_only_known_safe_actions():
    assert split_compound_commands("Open Spotify, then play Good Morning by Kanye West, and open YouTube with videos of cats") == ["Open Spotify","play Good Morning by Kanye West","open YouTube with videos of cats"]
    assert split_compound_commands("Open Steam and then open Discord") == ["Open Steam","open Discord"]
    assert split_compound_commands("Tell me about cats and dogs") == []


def test_deep_research_requires_an_imperative_and_extracts_only_the_topic():
    assert deep_research_command("Raven, do deep research on the history of cats") == "the history of cats"
    assert deep_research_command("Can you do deep research through the web for me?") is None
    assert deep_research_command("Is that from the Deep Research agent?") is None
    assert deep_research_command("On Research Lab do the history of the Aztecs please") == "the history of the Aztecs"


def test_voice_can_start_bounded_agent_missions_without_inferring_actions():
    assert mission_command("Raven, start a deep research mission on current Instagram API requirements") == {
        "template":"research","objective":"current Instagram API requirements","title":"Research: current Instagram API requirements"
    }
    assert mission_command("create a social media campaign for Atlanta technology jobs")["template"] == "social_campaign"
    assert mission_command("run a job search agent for remote SaaS sales roles")["template"] == "career_search"
    assert mission_command("we discussed a research mission yesterday") is None
    assert mission_command("run powershell to delete files") is None


def test_login_throttle_blocks_repeated_failures_and_clears_on_success():
    login_failures.clear();key="unit-client"
    for i in range(7):assert login_rate_state(key,False,100+i)[0]
    allowed,retry=login_rate_state(key,False,107)
    assert not allowed and retry>0
    assert login_rate_state(key,True,108)==(True,0)
    assert login_rate_state(key,None,109)==(True,0)


def test_capability_details_are_secret_free_and_actionable():
    career=detail_for("career")
    assert "Resume Creator" in career["summary"]
    assert career["models"] and career["milestones"] and career["voice_examples"]
    memory=detail_for("semantic_memory")
    assert "hybrid" in memory["summary"].lower() and "full-text" in " ".join(memory["runtime"]).lower()


def test_job_discovery_normalizes_deduplicates_and_scores_explainably():
    raw={"provider":"lever","external_id":"123","company":"Acme","title":"Account Development Representative","location":"Remote — US","description":"SaaS outbound sales CRM prospecting pipeline "*20,"source_url":"https://jobs.lever.co/acme/123","apply_url":"https://jobs.lever.co/acme/123/apply","metadata":{}}
    job=normalize(raw)
    assert job["fingerprint"] == fingerprint("lever","123",job["source_url"],job["title"],job["company"])
    assert matches(job,"account development",remote_only=True)
    score,reason=score_job(job["title"],job["description"],job["location"],["SaaS","CRM","prospecting"],{"search_preferences":"remote account development"})
    assert score>=70 and reason["matched_skills"]==["SaaS","CRM","prospecting"] and reason["method"]


def test_resume_artifacts_are_real_pdf_and_docx_files():
    resume="# Noah Candidate\nAtlanta · noah@example.com\n## EXPERIENCE\n- Built a qualified sales pipeline.\n## SKILLS\nSaaS, CRM"
    pdf=render_pdf(resume);docx=render_docx(resume)
    assert pdf.startswith(b"%PDF") and len(pdf)>500
    assert docx.startswith(b"PK") and len(docx)>1000
