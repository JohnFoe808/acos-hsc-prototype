# ACOS Website Reference

This document describes the current ACOS website and points to the implementation files.
For a portable visual mockup, open `ACOS_WEBSITE_REFERENCE.html` directly in a browser.

## Product identity

**ACOS — bounded simulation workspace**

The website is a local-first chatbot interface for the ACOS/HSC prototype. It is not
presented as proof of consciousness, AGI, ASI, or a real universe.

## Visual language

- Dark navy canvas with blue accents and mint online status.
- Rounded cards with compact typography.
- Three-column responsive layout inspired by a calculator/workspace:
  - **Chats rail**: saved conversations and New Chat.
  - **Chat canvas**: active thread, messages, prompt composer.
  - **Context rail**: attention, trusted-source search, compute, and privacy notes.
- Mobile layout collapses the columns into a single readable flow.
- User messages are right-aligned blue bubbles.
- ACOS messages are left-aligned dark bubbles.
- All message text is inserted as text, not HTML, to prevent markup injection.

## Current implementation map

| Area | File |
|---|---|
| FastAPI routes | `acos/main.py` |
| Chat executive | `acos/engine.py` |
| SQLite persistence | `acos/store.py` |
| Request/response models | `acos/schemas.py` |
| The World | `acos/world.py` |
| Trusted search boundary | `acos/search.py` |
| HTML shell | `static/index.html` |
| Visual styling | `static/styles.css` |
| Browser behavior | `static/app.js` |
| Server launcher | `scripts/start_server.py` |
| Repository app settings | `.github/github-app.yml` |

## Main user flows

### Ask a question

1. User types in the composer.
2. Browser sends `POST /api/message`.
3. The request includes the active conversation ID unless Incognito is enabled.
4. The executive records the user message, retrieves local memory, routes the task, and
   returns a bounded advisory result.
5. The browser renders the response defensively even if optional fields are missing.

### Save and revisit chats

1. `POST /api/conversations` creates a chat.
2. `GET /api/conversations` populates the left rail.
3. `POST /api/message` saves each turn automatically.
4. Selecting a chat calls `GET /api/conversations/{id}`.
5. `PATCH /api/conversations/{id}` renames it.

### Incognito

Incognito is a local persistence control, not an anonymity mechanism:

- no durable conversation ID is sent;
- no chat messages are written by the executive;
- local browser chat pointer is removed;
- no VPN, Tor, proxy, or traffic hiding is provided.

### Trusted search

The search panel calls `POST /api/search` only when the user submits a query.
The default request uses `network: false`, which returns a deterministic local result.
If a future provider is enabled, it must retain HTTPS and the trusted-domain allowlist,
timeouts, bounded results, and visible citations.

## API quick reference

```text
GET  /api/health
GET  /api/status
POST /api/message
GET  /api/conversations
POST /api/conversations
GET  /api/conversations/{id}
GET  /api/conversations/{id}/metadata
PATCH /api/conversations/{id}
POST /api/search
GET  /api/world
POST /api/world/entities
POST /api/world/time
```

## Run the real website

From the repository root:

```powershell
py -m pip install -e ".[dev]"
py scripts\start_server.py
```

Open:

```text
http://localhost:8000
```

## Rebuild prompt for another AI

> Rebuild the ACOS local-first chatbot from `ACOS_BUILD_CHRONOLOGY.md` and this
> reference. Preserve the FastAPI/SQLite architecture, persistent chats, memory,
> The World simulation, safe response rendering, and explicit simulation-only language.
> Keep Incognito local-only and do not implement VPN, Tor, Onion Browser, proxy,
> credential interception, unrestricted shell execution, or hidden network access.
> Use the existing static three-panel workspace as the visual baseline. Run tests,
> Ruff, and `node --check static\app.js` after changes.
