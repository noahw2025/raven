import asyncpg
from pgvector.asyncpg import register_vector
import json

SCHEMA = r"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), username text UNIQUE NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS conversations(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL DEFAULT 'New conversation', summary text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS messages(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id uuid REFERENCES conversations ON DELETE CASCADE, role text NOT NULL CHECK(role IN ('user','assistant','system')), content text NOT NULL, model text, tokens_in int DEFAULT 0, tokens_out int DEFAULT 0, cost_usd numeric(12,6) DEFAULT 0, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS memories(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, content text NOT NULL, kind text NOT NULL DEFAULT 'fact', importance int NOT NULL DEFAULT 3 CHECK(importance BETWEEN 1 AND 5), confidence real DEFAULT 1, sensitive boolean DEFAULT false, excluded boolean DEFAULT false, pinned boolean DEFAULT false, archived boolean DEFAULT false, source_type text NOT NULL DEFAULT 'manual', source_id uuid, rationale text NOT NULL DEFAULT '', supersedes_id uuid REFERENCES memories, embedding vector(1536), created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS documents(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, name text NOT NULL, mime text NOT NULL, sha256 text NOT NULL, status text DEFAULT 'ready', summary text DEFAULT '', created_at timestamptz DEFAULT now(), UNIQUE(user_id,sha256));
CREATE TABLE IF NOT EXISTS chunks(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), document_id uuid REFERENCES documents ON DELETE CASCADE, user_id uuid REFERENCES users ON DELETE CASCADE, ordinal int NOT NULL, content text NOT NULL, embedding vector(1536), created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS memory_usage(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), message_id uuid REFERENCES messages ON DELETE CASCADE, memory_id uuid REFERENCES memories ON DELETE CASCADE, reason text NOT NULL, score real, UNIQUE(message_id,memory_id));
CREATE TABLE IF NOT EXISTS citations(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), message_id uuid REFERENCES messages ON DELETE CASCADE, chunk_id uuid REFERENCES chunks ON DELETE CASCADE, rank int NOT NULL, score real);
CREATE TABLE IF NOT EXISTS goals(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL, detail text DEFAULT '', status text DEFAULT 'active', due_at timestamptz, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS tasks(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, goal_id uuid REFERENCES goals ON DELETE SET NULL, title text NOT NULL, detail text DEFAULT '', status text DEFAULT 'todo', priority int DEFAULT 3, due_at timestamptz, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS approvals(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, action text NOT NULL, reason text NOT NULL, target text NOT NULL, data_summary text NOT NULL, reversible boolean DEFAULT false, status text DEFAULT 'pending', payload jsonb NOT NULL DEFAULT '{}', expires_at timestamptz, decided_at timestamptz, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS audit(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE SET NULL, event text NOT NULL, entity_type text, entity_id text, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS integrations(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, name text NOT NULL, status text DEFAULT 'disconnected', access text DEFAULT 'none', approval_required boolean DEFAULT true, last_used_at timestamptz, UNIQUE(user_id,name));
CREATE TABLE IF NOT EXISTS memory_relations(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, source_id uuid REFERENCES memories ON DELETE CASCADE, target_id uuid REFERENCES memories ON DELETE CASCADE, relation text NOT NULL CHECK(relation IN ('related_to','supports','contradicts','supersedes','derived_from')), confidence real DEFAULT 1, created_at timestamptz DEFAULT now(), UNIQUE(source_id,target_id,relation));
CREATE TABLE IF NOT EXISTS runs(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL, objective text NOT NULL, template text NOT NULL DEFAULT 'general', department text NOT NULL DEFAULT 'Executive', status text NOT NULL DEFAULT 'queued', autonomy int NOT NULL DEFAULT 2 CHECK(autonomy BETWEEN 0 AND 5), budget_usd numeric(12,4) DEFAULT 1, spent_usd numeric(12,6) DEFAULT 0, result text DEFAULT '', error text DEFAULT '', created_at timestamptz DEFAULT now(), started_at timestamptz, finished_at timestamptz, updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS run_steps(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), run_id uuid REFERENCES runs ON DELETE CASCADE, ordinal int NOT NULL, title text NOT NULL, tool text NOT NULL, status text NOT NULL DEFAULT 'pending', approval_required boolean DEFAULT false, input jsonb NOT NULL DEFAULT '{}', output jsonb NOT NULL DEFAULT '{}', error text DEFAULT '', started_at timestamptz, finished_at timestamptz, UNIQUE(run_id,ordinal));
CREATE TABLE IF NOT EXISTS run_events(id bigserial PRIMARY KEY, run_id uuid REFERENCES runs ON DELETE CASCADE, event text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS notifications(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL, body text NOT NULL, severity text DEFAULT 'info', read_at timestamptz, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS tools(id text PRIMARY KEY, name text NOT NULL, category text NOT NULL, status text NOT NULL DEFAULT 'unavailable', capability text NOT NULL, risk text NOT NULL DEFAULT 'low', requires_approval boolean DEFAULT false, last_check_at timestamptz, detail text DEFAULT '');
CREATE TABLE IF NOT EXISTS model_usage(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE CASCADE, channel text NOT NULL, purpose text NOT NULL, provider text NOT NULL DEFAULT 'OpenAI', model text NOT NULL, input_tokens int NOT NULL DEFAULT 0, cached_input_tokens int NOT NULL DEFAULT 0, output_tokens int NOT NULL DEFAULT 0, input_audio_tokens int NOT NULL DEFAULT 0, cached_audio_tokens int NOT NULL DEFAULT 0, output_audio_tokens int NOT NULL DEFAULT 0, cost_usd numeric(12,8) NOT NULL DEFAULT 0, context_manifest jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS memory_decisions(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE CASCADE, source_message_id uuid REFERENCES messages ON DELETE SET NULL, memory_id uuid REFERENCES memories ON DELETE SET NULL, candidate text NOT NULL DEFAULT '', outcome text NOT NULL CHECK(outcome IN ('saved','review','duplicate','rejected','no_candidate')), reason_code text NOT NULL, confidence real NOT NULL DEFAULT 0, future_utility real NOT NULL DEFAULT 0, durability real NOT NULL DEFAULT 0, specificity real NOT NULL DEFAULT 0, evidence_quote text NOT NULL DEFAULT '', detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS social_accounts(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, provider text NOT NULL, external_account_id text NOT NULL DEFAULT '', handle text NOT NULL DEFAULT '', status text NOT NULL DEFAULT 'setup_required', permissions text[] NOT NULL DEFAULT '{}', last_verified_at timestamptz, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), UNIQUE(user_id,provider));
CREATE TABLE IF NOT EXISTS content_campaigns(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, name text NOT NULL, objective text NOT NULL, audience text NOT NULL, brand_voice text NOT NULL DEFAULT '', platforms text[] NOT NULL DEFAULT '{instagram}', status text NOT NULL DEFAULT 'draft', text_provider text NOT NULL DEFAULT 'active', text_model text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS content_assets(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id uuid REFERENCES content_campaigns ON DELETE CASCADE, kind text NOT NULL DEFAULT 'image_brief', provider text NOT NULL DEFAULT 'brief', model text NOT NULL DEFAULT '', prompt text NOT NULL DEFAULT '', public_url text NOT NULL DEFAULT '', status text NOT NULL DEFAULT 'brief_ready', metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS content_posts(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id uuid REFERENCES content_campaigns ON DELETE CASCADE, account_id uuid REFERENCES social_accounts ON DELETE SET NULL, platform text NOT NULL DEFAULT 'instagram', title text NOT NULL DEFAULT '', caption text NOT NULL, hashtags text[] NOT NULL DEFAULT '{}', asset_id uuid REFERENCES content_assets ON DELETE SET NULL, status text NOT NULL DEFAULT 'draft', scheduled_at timestamptz, published_at timestamptz, external_id text NOT NULL DEFAULT '', permalink text NOT NULL DEFAULT '', verification jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS content_events(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE SET NULL, campaign_id uuid REFERENCES content_campaigns ON DELETE CASCADE, post_id uuid REFERENCES content_posts ON DELETE CASCADE, event text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS career_profiles(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE UNIQUE, display_name text NOT NULL DEFAULT '', contact_summary text NOT NULL DEFAULT '', base_resume text NOT NULL DEFAULT '', skills text[] NOT NULL DEFAULT '{}', preferences jsonb NOT NULL DEFAULT '{}', updated_at timestamptz DEFAULT now(), created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS career_jobs(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL, company text NOT NULL, location text NOT NULL DEFAULT '', source_url text NOT NULL DEFAULT '', description text NOT NULL, application_questions jsonb NOT NULL DEFAULT '[]', status text NOT NULL DEFAULT 'saved', research_snapshot text NOT NULL DEFAULT '', research_sources jsonb NOT NULL DEFAULT '[]', discovered_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), UNIQUE(user_id,source_url));
CREATE TABLE IF NOT EXISTS resume_versions(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, job_id uuid REFERENCES career_jobs ON DELETE CASCADE, version int NOT NULL DEFAULT 1, label text NOT NULL, resume_markdown text NOT NULL, cover_letter text NOT NULL DEFAULT '', match_score int NOT NULL DEFAULT 0 CHECK(match_score BETWEEN 0 AND 100), strengths jsonb NOT NULL DEFAULT '[]', gaps jsonb NOT NULL DEFAULT '[]', provider text NOT NULL, model text NOT NULL, input_tokens int NOT NULL DEFAULT 0, output_tokens int NOT NULL DEFAULT 0, cost_usd numeric(12,8) NOT NULL DEFAULT 0, checksum text NOT NULL, created_at timestamptz DEFAULT now(), UNIQUE(job_id,version));
CREATE TABLE IF NOT EXISTS job_applications(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, job_id uuid REFERENCES career_jobs ON DELETE CASCADE, resume_version_id uuid REFERENCES resume_versions ON DELETE SET NULL, status text NOT NULL DEFAULT 'materials_ready', answers jsonb NOT NULL DEFAULT '[]', approval_id uuid REFERENCES approvals ON DELETE SET NULL, submitted_at timestamptz, verification jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), UNIQUE(user_id,job_id));
CREATE TABLE IF NOT EXISTS application_events(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE SET NULL, application_id uuid REFERENCES job_applications ON DELETE CASCADE, event text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS career_sources(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, provider text NOT NULL CHECK(provider IN ('greenhouse','lever','ashby')), tenant text NOT NULL, company text NOT NULL DEFAULT '', enabled boolean NOT NULL DEFAULT true, status text NOT NULL DEFAULT 'pending', last_sync_at timestamptz, last_count int NOT NULL DEFAULT 0, error text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), UNIQUE(user_id,provider,tenant));
CREATE TABLE IF NOT EXISTS career_searches(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, query text NOT NULL, location text NOT NULL DEFAULT '', remote_only boolean NOT NULL DEFAULT false, status text NOT NULL DEFAULT 'queued', result_count int NOT NULL DEFAULT 0, source_count int NOT NULL DEFAULT 0, error text NOT NULL DEFAULT '', criteria jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now(), finished_at timestamptz);
CREATE TABLE IF NOT EXISTS research_projects(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, title text NOT NULL, objective text NOT NULL, depth int NOT NULL DEFAULT 2 CHECK(depth BETWEEN 1 AND 3), status text NOT NULL DEFAULT 'queued', freshness text NOT NULL DEFAULT 'current', plan jsonb NOT NULL DEFAULT '{}', report text NOT NULL DEFAULT '', source_count int NOT NULL DEFAULT 0, finding_count int NOT NULL DEFAULT 0, input_tokens int NOT NULL DEFAULT 0, output_tokens int NOT NULL DEFAULT 0, cost_usd numeric(12,8) NOT NULL DEFAULT 0, error text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), started_at timestamptz, finished_at timestamptz, updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS research_queries(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid REFERENCES research_projects ON DELETE CASCADE, ordinal int NOT NULL, query text NOT NULL, rationale text NOT NULL DEFAULT '', status text NOT NULL DEFAULT 'pending', result_count int NOT NULL DEFAULT 0, error text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), UNIQUE(project_id,ordinal));
CREATE TABLE IF NOT EXISTS research_sources(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid REFERENCES research_projects ON DELETE CASCADE, query_id uuid REFERENCES research_queries ON DELETE SET NULL, source_index int NOT NULL, title text NOT NULL, url text NOT NULL, host text NOT NULL DEFAULT '', published_at text NOT NULL DEFAULT '', excerpt text NOT NULL DEFAULT '', fetched boolean NOT NULL DEFAULT false, quality text NOT NULL DEFAULT 'unknown', created_at timestamptz DEFAULT now(), UNIQUE(project_id,url));
CREATE TABLE IF NOT EXISTS research_findings(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid REFERENCES research_projects ON DELETE CASCADE, ordinal int NOT NULL, claim text NOT NULL, confidence real NOT NULL DEFAULT 0, source_indexes int[] NOT NULL DEFAULT '{}', caveat text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(), UNIQUE(project_id,ordinal));
CREATE TABLE IF NOT EXISTS research_events(id bigserial PRIMARY KEY, user_id uuid REFERENCES users ON DELETE SET NULL, project_id uuid REFERENCES research_projects ON DELETE CASCADE, event text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS forge_projects(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, display_name text NOT NULL, repo_path text NOT NULL, default_branch text NOT NULL DEFAULT 'main', allowed_commands jsonb NOT NULL DEFAULT '[]', runtime_metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), UNIQUE(user_id,repo_path));
CREATE TABLE IF NOT EXISTS forge_jobs(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES users ON DELETE CASCADE, project_id uuid REFERENCES forge_projects ON DELETE CASCADE, conversation_id uuid REFERENCES conversations ON DELETE SET NULL, title text NOT NULL, user_request text NOT NULL, status text NOT NULL DEFAULT 'queued', execution_mode text NOT NULL DEFAULT 'build', provider_policy text NOT NULL DEFAULT 'auto', selected_provider text NOT NULL DEFAULT '', selected_model text NOT NULL DEFAULT '', runtime text NOT NULL DEFAULT 'Hermes', branch text NOT NULL DEFAULT '', base_commit text NOT NULL DEFAULT '', current_iteration int NOT NULL DEFAULT 0, max_iterations int NOT NULL DEFAULT 12, max_runtime_seconds int NOT NULL DEFAULT 1800, current_stage text NOT NULL DEFAULT 'queued', summary text NOT NULL DEFAULT '', failure_reason text NOT NULL DEFAULT '', pause_requested boolean NOT NULL DEFAULT false, cancel_requested boolean NOT NULL DEFAULT false, started_at timestamptz, completed_at timestamptz, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS forge_job_events(id bigserial PRIMARY KEY, job_id uuid REFERENCES forge_jobs ON DELETE CASCADE, event_type text NOT NULL, stage text NOT NULL DEFAULT '', summary text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS forge_messages(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_id uuid REFERENCES forge_jobs ON DELETE CASCADE, role text NOT NULL CHECK(role IN ('user','assistant','system')), content text NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS forge_artifacts(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_id uuid REFERENCES forge_jobs ON DELETE CASCADE, kind text NOT NULL, label text NOT NULL, content text NOT NULL DEFAULT '', metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz DEFAULT now());
ALTER TABLE memories ADD COLUMN IF NOT EXISTS review_state text NOT NULL DEFAULT 'confirmed';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS use_count int NOT NULL DEFAULT 0;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS last_used_at timestamptz;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS local_embedding vector(768);
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS local_embedding vector(768);
ALTER TABLE model_usage ADD COLUMN IF NOT EXISTS latency_ms int NOT NULL DEFAULT 0;
ALTER TABLE model_usage ADD COLUMN IF NOT EXISTS prompt_chars int NOT NULL DEFAULT 0;
ALTER TABLE model_usage ADD COLUMN IF NOT EXISTS response_chars int NOT NULL DEFAULT 0;
ALTER TABLE research_projects ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT '';
ALTER TABLE research_projects ADD COLUMN IF NOT EXISTS model text NOT NULL DEFAULT '';
ALTER TABLE research_projects ADD COLUMN IF NOT EXISTS answer_quality text NOT NULL DEFAULT 'pending';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS application_questions jsonb NOT NULL DEFAULT '[]';
ALTER TABLE career_profiles ADD COLUMN IF NOT EXISTS application_defaults jsonb NOT NULL DEFAULT '{}';
ALTER TABLE career_profiles ADD COLUMN IF NOT EXISTS career_facts jsonb NOT NULL DEFAULT '{}';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS source_provider text NOT NULL DEFAULT 'manual';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS external_id text NOT NULL DEFAULT '';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS apply_url text NOT NULL DEFAULT '';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS posted_at timestamptz;
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS workplace_type text NOT NULL DEFAULT '';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS salary text NOT NULL DEFAULT '';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS fingerprint text NOT NULL DEFAULT '';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS fit_score int NOT NULL DEFAULT 0;
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS fit_rationale jsonb NOT NULL DEFAULT '{}';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE career_jobs ADD COLUMN IF NOT EXISTS search_id uuid REFERENCES career_searches ON DELETE SET NULL;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS idempotency_key text NOT NULL DEFAULT '';
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS attempt_count int NOT NULL DEFAULT 0;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS last_error text NOT NULL DEFAULT '';
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS last_attempt_at timestamptz;
CREATE INDEX IF NOT EXISTS chunks_user_idx ON chunks(user_id);
CREATE INDEX IF NOT EXISTS memories_user_idx ON memories(user_id) WHERE archived=false AND excluded=false;
CREATE INDEX IF NOT EXISTS audit_user_created_idx ON audit(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS memories_local_embedding_hnsw ON memories USING hnsw (local_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_local_embedding_hnsw ON chunks USING hnsw (local_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS runs_user_status_idx ON runs(user_id,status,updated_at DESC);
CREATE INDEX IF NOT EXISTS model_usage_user_created_idx ON model_usage(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS memory_decisions_user_created_idx ON memory_decisions(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS content_campaigns_user_created_idx ON content_campaigns(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS content_posts_campaign_status_idx ON content_posts(campaign_id,status,created_at DESC);
CREATE INDEX IF NOT EXISTS content_events_user_created_idx ON content_events(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS career_jobs_user_updated_idx ON career_jobs(user_id,updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS career_jobs_user_fingerprint_unique ON career_jobs(user_id,fingerprint) WHERE fingerprint<>'';
CREATE INDEX IF NOT EXISTS career_sources_user_enabled_idx ON career_sources(user_id,enabled);
CREATE INDEX IF NOT EXISTS career_searches_user_created_idx ON career_searches(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS resume_versions_job_version_idx ON resume_versions(job_id,version DESC);
CREATE INDEX IF NOT EXISTS job_applications_user_status_idx ON job_applications(user_id,status,updated_at DESC);
CREATE INDEX IF NOT EXISTS application_events_user_created_idx ON application_events(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS research_projects_user_updated_idx ON research_projects(user_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS research_sources_project_idx ON research_sources(project_id,source_index);
CREATE INDEX IF NOT EXISTS research_findings_project_idx ON research_findings(project_id,ordinal);
CREATE INDEX IF NOT EXISTS forge_projects_user_idx ON forge_projects(user_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS forge_jobs_user_idx ON forge_jobs(user_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS forge_jobs_queue_idx ON forge_jobs(status,created_at) WHERE status IN ('queued','resuming');
CREATE INDEX IF NOT EXISTS forge_job_events_job_idx ON forge_job_events(job_id,id);
UPDATE memory_decisions SET confidence=least(1,greatest(0,confidence)),future_utility=least(1,greatest(0,future_utility)),durability=least(1,greatest(0,durability)),specificity=least(1,greatest(0,specificity));
"""


class Database:
    pool: asyncpg.Pool | None = None

    async def connect(self, url: str) -> None:
        # pgvector's asyncpg codec can only register after the extension's
        # vector type exists. Bootstrap it on a plain connection first.
        bootstrap = await asyncpg.connect(url, command_timeout=30)
        try:
            await bootstrap.execute("CREATE EXTENSION IF NOT EXISTS vector")
        finally:
            await bootstrap.close()
        async def configure(conn):
            await register_vector(conn)
            encode_json=lambda value: value if isinstance(value,str) else json.dumps(value)
            await conn.set_type_codec('json',schema='pg_catalog',encoder=encode_json,decoder=json.loads)
            await conn.set_type_codec('jsonb',schema='pg_catalog',encoder=encode_json,decoder=json.loads)
        self.pool = await asyncpg.create_pool(url, init=configure, min_size=1, max_size=10, command_timeout=30)
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA)
            await conn.execute("INSERT INTO users(username) VALUES('owner') ON CONFLICT DO NOTHING")
            uid = await conn.fetchval("SELECT id FROM users WHERE username='owner'")
            for name in ('Hermes Runtime','Web Search','Desktop Gateway','Home Assistant','Email','Calendar','Instagram','ComfyUI','Discord','Steam','Spotify','Career Automation'):
                await conn.execute("INSERT INTO integrations(user_id,name) VALUES($1,$2) ON CONFLICT DO NOTHING",uid,name)
            tool_rows = [
                ('openai_chat','Provider-neutral reasoning','AI','ready','Conversation, planning, extraction through the active provider','low',False,'Qwen3 8B through local Ollama; OpenAI remains an interchangeable fallback'),
                ('content_text','Local content strategist','Marketing','ready','Campaign strategy, hooks, captions, hashtags, and generation evidence','low',False,'Provider-neutral adapter; Qwen3 8B shares the resident local runtime to avoid model-swap latency at $0 API cost'),
                ('content_image','ComfyUI media engine','Marketing','unavailable','Local image and video workflow execution','medium',False,'Set COMFYUI_URL and approve a versioned workflow before generation'),
                ('semantic_memory','Hybrid semantic memory','Memory','ready','Evidence-gated extraction plus vector, lexical, and fused retrieval','medium',False,'nomic-embed-text + pgvector HNSW + PostgreSQL full-text ranking; $0 API cost'),
                ('web_research','Private web research','Research','ready','Current metasearch with traceable output','medium',False,'Self-hosted SearXNG + local synthesis'),
                ('deep_research','Deep Research worker','Research','ready','Plan multiple searches, fetch sources, synthesize cited findings, and verify the report','medium',False,'Persistent local worker: SearXNG + bounded public pages + Qwen3 planning/synthesis/reflection'),
                ('youtube_search','YouTube discovery','Media','ready','Find current public YouTube videos by voice or text and return verified source links','low',False,'Keyless public search through the private metasearch route; playback opens only an explicit YouTube URL'),
                ('local_voice','Local voice pipeline','Voice','ready','Faster-Whisper transcription + Qwen voice reasoning + Kokoro speech','low',False,'Browser-active ARISE wake phrase; raw microphone audio stays inside the local Docker network'),
                ('hermes','Hermes worker','Runtime','unavailable','Long-running computer and coding work','high',True,'Configure HERMES_URL and HERMES_TOKEN'),
                ('desktop','Desktop gateway','Action','unavailable','Allowlisted local application control','high',True,'No gateway configured'),
                ('spotify','Spotify control','Media','unavailable','Open Spotify, search exact songs, and optionally confirm OAuth playback','medium',False,'Keyless app/search works through the host companion; playback needs owner OAuth and an active Premium device'),
                ('social','Instagram publishing','Action','unavailable','Approval-gated Instagram Professional content publishing','high',True,'Server-side Meta token required; credentials are never returned to the browser'),
                ('career','Career preparation','Career','ready','Import jobs, research hiring signals, tailor resumes, write cover letters, and answer prompts','medium',False,'Local Qwen3 generation with immutable Postgres versions and exact model-usage evidence'),
                ('career_apply','Supervised job submission','Career','unavailable','Fill and submit an approved application through a typed browser adapter','high',True,'Configure CAREER_APPLY_URL and token; successful submission must return confirmation evidence'),
                ('brokerage','Brokerage','Finance','blocked','Research and supervised orders','critical',True,'Live trading intentionally blocked'),
            ]
            for row in tool_rows:
                await conn.execute("INSERT INTO tools(id,name,category,status,capability,risk,requires_approval,detail,last_check_at) VALUES($1,$2,$3,$4,$5,$6,$7,$8,now()) ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,status=excluded.status,capability=excluded.capability,risk=excluded.risk,requires_approval=excluded.requires_approval,detail=excluded.detail,last_check_at=now()",*row)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()


db = Database()
