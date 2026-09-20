# ACOS Build Chronology

This file records the project in chronological order so another AI or developer can
rebuild the website without losing the safety boundaries or the decisions already made.

## 1. Source prototype and boundaries

- Started from the attached `RITAC_Unified_v02 (2).zip` and the ACOS/HSC prototype.
- Established the project as a bounded research prototype.
- ASC/AC, AGI-like, and ASI-like behavior are simulations only.
- The software must not be described as proof of consciousness, AGI, or ASI.
- No arbitrary shell execution, unrestricted self-modification, secrets, credentials, or
  network-dependent simulator behavior.

## 2. Bounded terminal simulator

Created `asc_simulator.py` with:

- attention and Global Workspace state;
- episodic, semantic, and working memory;
- ranked recall;
- bounded planning and simulation cycles;
- explicit `simulation_only: true` claims;
- persistent optional JSON state;
- `status`, `demo`, and interactive `shell` commands.

Added `tests/test_asc_simulator.py` and documented the terminal in `README.md`.

## 3. Repository app configuration

Created `.github/github-app.yml` with:

- repository-specific safety instructions;
- development dependency installation;
- ASC demo and terminal commands;
- test command;
- ACOS server launch command;
- port detection and browser preview behavior;
- remote control disabled.

## 4. ACOS web application

The existing FastAPI/PWA prototype provides:

- SQLite persistence;
- Global Workspace and cognitive event loop;
- memory and skill APIs;
- permission broker;
- CPU/GPU/QPU-oriented compute routing;
- deterministic quantum simulator adapter;
- hybrid DAG execution;
- model-core abstraction with deterministic mock fallback;
- verification and audit records;
- PWA static frontend.

The default model provider is local deterministic mock behavior. Optional
OpenAI-compatible providers are explicit configuration, not required for local use.

## 5. Local ASC/AC chatbot

Added a chatbot through `POST /api/message`:

- greetings and normal conversational prompts;
- direct bounded answers;
- step-by-step tutoring prompts;
- `remember that ...`;
- `recall ...` and memory questions;
- structured plans with route, confidence, verification, and uncertainty;
- durable conversation messages;
- context metadata for future multimodal inputs without uploading or interpreting files.

Every response carries the simulation boundary: the system makes no claim of real
subjective consciousness, AGI, or ASI.

## 6. The World micro-universe

Added `acos/world.py` and durable World state:

- name: **The World**;
- deterministic clock and tick advancement;
- entities and locations;
- bounded event history;
- chatbot intents for World status, adding entities, and advancing time;
- API routes for status, entities, and time.

The World is a local simulation, not a real universe or autonomous conscious world.

## 7. Error fixes and localhost launcher

Fixed frontend plan rendering so array-shaped and object-shaped plans do not call
`.map()` on a non-array.

Added `scripts/start_server.py` and changed documentation/configuration to use it.
The launcher uses the active Python interpreter, binds to `0.0.0.0` by default, and
honors `ACOS_HOST`, `ACOS_PORT`, and `ACOS_RELOAD`.

Verified:

```text
http://localhost:8000/
http://localhost:8000/api/health
```

## 8. Persistent chats

Added a durable `conversations` table and chat management:

- create a new chat;
- list saved chats;
- automatically save every user and assistant message;
- revisit a saved chat;
- rename a chat;
- restore the selected chat from browser local storage;
- migrate older `chat_messages` rows into conversation metadata.

Relevant routes:

```text
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{id}
GET    /api/conversations/{id}/metadata
PATCH  /api/conversations/{id}
POST   /api/message
```

## 9. Desmos-like workspace and privacy boundary

Reworked the frontend into a compact three-panel workspace:

- left rail: chats and New Chat;
- center: conversation canvas and composer;
- right rail: attention, World/context, compute, and search.

Added Incognito mode. It:

- omits the conversation ID;
- skips durable chat-message writes;
- clears the browser chat pointer;
- keeps the current session ephemeral.

Incognito is **not** a VPN, Onion Browser, proxy, or anonymity guarantee.
No Tor, VPN, proxy, traffic interception, or credential handling was added.

## 10. Trusted-source search boundary

Added `acos/search.py` and `POST /api/search`:

- opt-in only;
- network disabled by default;
- deterministic local fallback;
- HTTPS validation;
- allowlisted `.gov`, `.edu`, `.org`, and selected public documentation hosts;
- bounded, citation-ready result shape.

The project does not claim perfect answers or superintelligence. It reports uncertainty
and keeps outputs advisory.

## 11. Current verification

The project has been repeatedly checked with:

```powershell
py -m pytest -q
py -m ruff check acos tests scripts
py -m ruff format --check acos tests scripts
node --check static\app.js
```

The current implementation has passed the focused and regression checks used during
development. FastAPI/httpx may still emit dependency deprecation warnings that do not
indicate an application failure.

## Rebuild order for another AI

1. Read this file and `README.md`.
2. Read `.github/github-app.yml` before running commands.
3. Read `pyproject.toml`, `acos/main.py`, `acos/engine.py`, `acos/store.py`, and
   `acos/schemas.py`.
4. Read `static/index.html`, `static/styles.css`, and `static/app.js`.
5. Preserve the simulation-only and privacy boundaries.
6. Run the tests before changing behavior.
7. Make small changes, then rerun tests, Ruff, and the JavaScript syntax check.
