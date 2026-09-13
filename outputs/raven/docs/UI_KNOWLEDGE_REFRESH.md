# Workspace and knowledge-map refresh — September 3, 2026

## Navigation

Thirteen primary sidebar destinations are consolidated into eight activity workspaces:

| Workspace | Local views |
| --- | --- |
| Assistant | Overview, Conversation |
| Research | Research Lab, Search setup |
| Career | Existing discovery, profile and application views |
| Content | Existing campaigns, drafts and media workflow |
| Work | Background work, Goals & tasks, Approvals |
| Knowledge | Vector map, Memory library, How memory works |
| Capabilities | Connections, Build roadmap, Departments |
| System | Activity, Models & costs, Privacy & settings |

The duplicate operations tab strip is removed from Capabilities. Its model-cost, memory-engine and search details have one navigation home above. Existing route names and voice navigation remain compatible. No user data or capability was removed.

## Visual system

Shared navy surfaces, cyan circuitry accents, amber warnings, readable secondary text, rounded panels, consistent spacing and visible focus states replace the low-contrast green styling. Eight-workspace rail, local view tabs and a responsive detail drawer preserve the existing application structure. Reduced-motion preferences are respected.

## Real vector map

The server computes deterministic PCA over normalized stored vectors. Memory embeddings and document chunk-vector centroids share the same projection. Raw vectors stay server-side. At most 500 objects are projected; unprojected objects use a clearly identified separate rail. The current live data projects 85 objects and retains approximately 27% of variance in three dimensions: this is a lossy overview, not an exact semantic-distance or confidence visualization. Similarity edges still come from full-dimensional cosine similarity, rather than 3D screen distances.

Small clickable nodes, label collision avoidance, search, type filtering, 2D/3D/list modes, keyboard activation, and rotation/zoom remain available. Dense labels may be suppressed; search or list mode reveals individual objects. Document centroids summarize their chunks and can hide differences within long documents.

Click a memory node to open an accessible dialog independent of sidebar visibility. It supports editing text/category/importance, excluding retrieval, saving a recalculated embedding, and explicit permanent-delete confirmation. Other object types open their own workspaces rather than masquerading as editable memories.

## Verification

- 955 core, command, background-tool and vector tests passed.
- All eight primary destinations rendered without recorded browser errors.
- Capabilities no longer exposes its duplicate tab strip; Models & costs opens under System.
- Live browser test created a temporary excluded memory, clicked its SVG node, edited/saved it, verified its new label, and tested deletion confirmation/cancellation.
- API readback verified the edit persisted. Only that test fixture was then permanently deleted through the API; the graph no longer returned it. No pre-existing user memories were removed.
- Visual inspection covered the new Knowledge layout and palette. Real mobile-device and cross-browser acceptance remain useful follow-up checks.

Files: `app/static/workspace.js`, `app/static/workspace.css`, `app/vector_layout.py`, graph endpoint in `app/main.py`, and `tests/test_vector_layout.py`.
