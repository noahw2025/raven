# Voice-connected background tools

Updated September 3, 2026. This is an implementation and test record, not a claim that every planned connector is production-ready.

## Commands to try

Voice and text use the same typed dispatcher. Polite prefixes, punctuation and explicit chains are supported. Examples:

- “Find sales jobs in Atlanta in the background.”
- “Can you look for remote account executive jobs while we talk?”
- “What did my job search find?”
- “Tailor my resume for the first job.” (Uses the completed search in this conversation.)
- “Prepare an application for job Account Executive at Example Company.” (Exact unique saved title and company.)
- “Apply for the second job.” (Prepares materials and requests review; does not approve or submit.)
- “Submit approved application <application ID>.” (Requires a connected submission adapter and a valid approval for this exact application and resume version.)
- “Start an in-depth research agent on battery recycling.”
- “What did the research agent find?”
- “Summarize my research results.”
- “Create a content campaign about gardening for Instagram.”
- “Generate posts about home robotics for YouTube.”
- “What did my content task produce?”
- “Generate media for the first post.” (Uses the latest completed content task in this conversation and its saved image/video brief.)
- “Show my background tasks.”
- “Find sales jobs in Atlanta, then research solar technology, then create a content campaign about solar power.”

The last example starts three independent tasks. It does **not** imply that content consumed the research results. For dependent work, wait for results and specify the next step. “Then tailor the first job” before the search has completed is rejected rather than selecting a different job. Eight active tasks per owner and eight actions per chain are the current limits.

## Execution and evidence

1. Local microphone audio is transcribed, then uses the same `/api/chat` route as typed input.
2. `assistant_jobs.parse_command` recognizes an allowlisted action, never generated code or arbitrary endpoints.
3. Target resolution is owner-scoped. Exact saved IDs or unique titles are accepted; numbered job/post references are resolved only against completed results in the current conversation.
4. PostgreSQL `assistant_jobs` persists the owner, conversation, typed payload, status and result. Duplicate active requests in the same conversation are reused.
5. A lifespan-managed worker calls the real Career/Content endpoints, or queues the existing Research/ComfyUI workers. A queue acknowledgment is not a completion claim.
6. Career outputs land in the existing jobs, resume versions and application ledger. Content outputs land in campaigns, posts and assets. Research preserves its report, sources and findings.
7. Research and ComfyUI remain waiting until their domain reports completion or failure. Model usage is recorded by the domain services; saved-result discussion also records usage.
8. Missions → Voice + Text Background Tasks shows persisted tasks, command examples and inspectable evidence. Completion/failure notifications appear without interrupting microphone capture. Ask for results to hear them spoken.

Explicit result questions use the saved task result, not a new web search or a new project. Ordinary follow-up conversation receives bounded latest-task context (14,000 characters); explicit result summaries receive at most 16,000 characters. Large reports are therefore bounded, not sent wholesale without limit.

## Safety and recovery

- Secrets remain server-side. No provider keys are added to frontend responses.
- Application preparation never approves itself. Submission checks owner, application, resume version, approval expiry and adapter readiness; already submitted applications are rejected.
- No publishing is performed by these new background voice routes. Platform credentials, public media hosting, approval and a supported publisher remain separate requirements. YouTube upload is still an incomplete adapter.
- Started work interrupted by a service restart is marked failed, preserving saved artifacts; it is not automatically replayed. Queued jobs remain queued; Research/ComfyUI waiting jobs remain linked to their domain state.
- Tasks have a 15-minute execution deadline; a timeout does not prove an external action was cancelled. Inspect the domain evidence before retrying. One local task executes at a time to limit load; Research has its own worker.
- Unknown/ambiguous targets cause clarification. Unsupported commands are not promoted into arbitrary shell or browser control.

## Verification performed

- Existing command-chain/core regressions plus new parser/dispatch/ownership tests: 952 passed.
- Voice lifecycle checks: 9 passed.
- Live text/voice routing: same active job search reused rather than duplicated; missing application target rejected.
- Real Career search: 12 saved matches for sales jobs in Atlanta. This verifies execution and persistence, not that every match is personally suitable.
- Real content task: three saved Instagram drafts, with a correct follow-up describing their garden-care topics.
- Real research: completed with 26 sources and 10 findings. Quality of every claim has not been independently re-audited in this pass.
- Research result follow-up returned findings from the completed project, with the task count unchanged at three (no accidental new research).
- Synthetic audio → actual local STT → saved content-task answer → actual local TTS: passed. This is not a physical microphone, room-noise or barge-in test.
- Browser UI: Missions displayed the three real background tasks and their states.
- No live application submission, social publishing or new ComfyUI render was executed in this pass. Their dispatch seams are tested without sending personal information or publishing test content.

## Next acceptance gates

1. Real-room Chrome microphone test with pauses, interruptions and task-result follow-ups.
2. Connect and pilot a supervised application adapter with one explicitly approved target and provider confirmation.
3. Test media generation against a saved post, then configure one publishing sandbox with approval-bound content snapshots.
4. Add a dependency-aware plan graph, cancellation semantics, per-task budgets and concurrency controls before promising arbitrary autonomous multi-step workflows.
5. Add per-task report retrieval for very long results, worker soak/restart tests, and richer result cards instead of raw record inspection.
