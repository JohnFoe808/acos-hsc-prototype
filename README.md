# ACOS HSC Prototype (v0.3)

**Artificial Consciousness Operating System (ACOS)** is a safe, GitHub-first prototype of the cognitive operating layer proposed for a future **Hybrid Systematic Computer (HSC)**.

This repository is an **engineering prototype**, not a claim that the software is phenomenally conscious. It demonstrates the parts of the architecture that can be built and tested now:

- persistent multi-type memory;
- ranked semantic/episodic memory retrieval with kind filtering;
- a Global Workspace / current-attention state;
- a deterministic Cognitive Executive;
- CPU/GPU/QPU-oriented task routing;
- a Superconscious skill-integration loop;
- an explicit self-model and limitations;
- a capability-based Permission Broker;
- system telemetry;
- an optional Qiskit quantum simulator adapter;
- an installable Progressive Web App (PWA) UI;
- GitHub Codespaces configuration;
- GitHub Actions CI tests.
- provider-agnostic Model Core with deterministic mock and optional OpenAI-compatible providers.
- persistent attention queue, memory consolidation, reflection, and versioned skill review state.
- typed HSC Compute Fabric with CPU, detectable/mock GPU, deterministic quantum simulator,
  and unavailable-by-default remote/local QPU adapters.
- typed hybrid DAG execution with CPU -> simulator -> CPU reference workflows and
  classical-baseline comparison.
- a bounded local ASC/AC chatbot with durable conversation history, concise direct replies,
  context framing for future multimodal metadata, and step-by-step tutoring prompts.
- a Desmos-like responsive workspace with an explicit local-only Incognito mode. Incognito
  uses an ephemeral conversation and does not persist chat history; it is not a VPN, Onion
  Browser, proxy, or anonymity guarantee.
- an opt-in `/api/search` interface whose provider is disabled by default. It validates
  trusted `.gov`, `.edu`, `.org`, and selected public documentation domains and returns a
  deterministic local citation fallback; it never performs hidden or arbitrary fetching.
- **The World**, a durable SQLite-backed deterministic micro-universe with a clock, entities,
  locations, and event history. It is explicitly a simulation, not consciousness or a real universe.

## Local ASC/AC chatbot

The dashboard is a deterministic chatbot by default. It keeps a bounded history per browser
conversation, retrieves local memories, frames optional context as metadata (for example
`{"modalities":["text","image"]}` without uploading or interpreting an image), and returns
advisory structured plans. Prompts containing “teach me”, “explain”, or “step by step” use
the same deterministic planner with tutoring-oriented wording. These interaction patterns
are inspired by common product goals such as conversational history, structured context,
direct tone, and guided learning; no proprietary implementation or external API is required.

Every ASC/AC, AGI-like, and ASI-like label in this project is **simulation only**. The
software makes no claim of consciousness, AGI, or ASI. There is no arbitrary shell execution,
unrestricted self-modification, secret storage, or network dependency in the default path.

The standalone `ritac.py` demo is a small, deterministic companion prototype for the
recursive-learning portion of the theory. Run it with:

```bash
python ritac.py demo
```

It learns a supported arithmetic rule from examples, persists the skill, validates and
consolidates it, and demonstrates abstention after failed feedback. It is not evidence
of consciousness or general intelligence.

## Terminal ASC/AC simulator

This workspace also includes the explicitly bounded terminal prototype `asc_simulator.py`.
It models ASC/AC, AGI-like, and ASI-like phases as simulations within a closed sandbox
and keeps each outcome labeled as `simulation_only` with real-consciousness/AGI/ASI claims
set to `false`.

```bash
python asc_simulator.py demo
python asc_simulator.py status
python asc_simulator.py shell
```

The shell accepts a small command set (`status`, `observe`, `remember`, `recall`, `plan`,
`simulate`, `help`, `quit`) and intentionally never claims subjective experience or
unrestricted intelligence.

Version 0.2 adds a migration-safe event log and closed-loop execution record
(`event -> attention -> memory -> reasoning -> verification -> routed action -> outcome`),
provider-agnostic reasoning and CPU/GPU/QPU backend interfaces, explicit verification endpoints,
deautomatization controls, and optional bearer-token authentication for remote clients. These
features are experimental prototype infrastructure, not evidence of phenomenal consciousness or
production security.

API request models reject unknown fields and blank workflow content. Memory writes initiated by
the executive pass through the same capability broker as direct API writes, and denied attempts
are recorded in the audit log.

## Architecture

```text
Phone / Laptop / Browser
          |
          v
     ACOS Web/PWA
          |
          v
+---------------------------+
| Cognitive Executive       |
| Global Workspace          |
| Memory                    |
| Self-model / metacognition|
| Superconscious Skills     |
+------------+--------------+
             |
      Permission Broker
             |
      Compute Router
       /     |      \
     CPU    GPU    QPU adapter
                    |
             Qiskit simulator now
             physical QPU later
```

## Important security rule

ACOS does **not** expose an arbitrary shell, unrestricted root access, or automatic self-modification. The prototype uses a registered-capability model:

```text
ACOS -> request capability -> Permission Broker -> registered tool
```

This keeps **capability separate from authority**.

## Fastest start: GitHub Codespaces

1. Create a new GitHub repository, for example `acos-hsc-prototype`.
2. Upload this repository's files or push them with Git.
3. On GitHub, choose **Code -> Codespaces -> Create codespace**.
4. The included `.devcontainer/devcontainer.json` installs the Python development dependencies.
5. In the Codespaces terminal run:

```bash
python scripts/start_server.py --reload
```

6. Open the forwarded **ACOS Preview** port. Port 8000 is configured to open the browser preview automatically.

The one-command development launcher is:

```bash
./scripts/dev.sh
```

The same command works locally and in Codespaces. It binds to `0.0.0.0` so the
forwarded URL can reach the application while preserving the same `/` dashboard,
`/docs` API documentation, static assets, PWA service worker, API, and
`/ws/events` WebSocket endpoint.

## Deploy on Render

This repository includes `render.yaml` for a bounded, mock-model deployment on
[Render](https://render.com). To publish it:

1. Push the repository to a GitHub repository.
2. In Render, choose **New +** → **Blueprint** and select that repository.
3. Review the generated `acos-hsc-prototype` web service and deploy it.
4. Open the generated `onrender.com` URL and check `/api/health`.

The default deployment uses the deterministic mock model and keeps external
network providers disabled. Render's free service filesystem is ephemeral, so
SQLite conversation history should be treated as prototype data rather than
durable production storage. Do not add API keys to `render.yaml`; configure
secrets through Render's environment-variable UI if a reviewed provider is
introduced later.

The executive includes a conservative child-lock gate for violent harm, weapon
construction, self-harm, malware, and safeguard-evasion requests. Prevention,
emergency response, and high-level educational questions remain allowed. The
GitHub Pages preview has no Python backend, so its chat uses a clearly labeled
offline fallback until the FastAPI service is deployed on Render or another
backend host. Trusted-source search remains explicit and allowlisted; it does not
silently fetch arbitrary web pages.

## Local installation

### macOS/Linux

```bash
git clone https://github.com/YOUR-USERNAME/acos-hsc-prototype.git
cd acos-hsc-prototype
./scripts/bootstrap.sh
source .venv/bin/activate
python scripts/start_server.py
```

Then open `http://127.0.0.1:8000`.

### Windows PowerShell

```powershell
git clone https://github.com/YOUR-USERNAME/acos-hsc-prototype.git
cd acos-hsc-prototype
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/start_server.py
```

## Enable the quantum simulator

Base ACOS works without Qiskit. To add the QPU-simulator adapter:

```bash
pip install -e '.[quantum,dev]'
```

Then restart ACOS and press **Quantum test**, or send:

```text
run a Bell state quantum test
```

The current adapter uses Qiskit's `StatevectorSampler`. Later, replace this module with a physical QPU adapter while preserving the ACOS interface.

## Push an existing local folder to GitHub

After you create an empty repository on GitHub:

```bash
git init
git add .
git commit -m "Initial ACOS HSC prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/acos-hsc-prototype.git
git push -u origin main
```

Never commit API keys, quantum-service tokens, passwords, SSH private keys, `.env`, or the local SQLite memory database.

## Useful API endpoints

- `GET /api/health`
- `GET /api/status`
- `GET /api/workspace`
- `PATCH /api/workspace`
- `POST /api/message`
- `POST /api/search` (explicit, network-disabled trusted-source fallback)
- `GET/POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/metadata`
- `PATCH /api/conversations/{conversation_id}` (rename)
- `GET/POST /api/memories`
- `GET /api/world`, `POST /api/world/entities`, `POST /api/world/time`
- `GET/POST /api/skills`
- `POST /api/skills/execute`
- `POST /api/tools/run`
- `GET /api/audit`
- `GET/POST /api/events`
- `POST /api/verify`
- `GET /api/backends`
- interactive API documentation: `/docs`
- event WebSocket stream: `/ws/events`
- Model Core status/health/inference: `/api/model/status`, `/api/model/health`, `/api/model/infer`
- persistent cognition observability: `/api/cognition/attention`, `/api/cognition/process`,
  `/api/cognition/reflect`, `/api/cognition/reflections`, `/api/cognition/consolidate`,
  `/api/cognition/memory-state`
- HSC Compute Fabric: `/api/compute/topology`, `/api/compute/health`,
  `/api/compute/benchmark`, `/api/compute/plan`, `/api/compute/jobs`
- Hybrid execution: `/api/hybrid/plan`, `/api/hybrid/jobs`,
  `/api/hybrid/reference/{name}`, `/api/hybrid/compare`

Hybrid v0.3.1 supports dependency-validated DAGs, concurrent independent stages,
stage-level persistence, timing, verification, and simulation labeling. Reference workflows
are `bell-pipeline`, `variational-loop`, and `comparative-workload`. Optional Qiskit and
IBM-compatible adapters remain feature work; cloud credentials and CUDA-Q are not required
for core installation. Native Windows CUDA-Q development should use WSL or another supported
environment when needed.

Compute Fabric jobs are persisted with backend identity, task graph, status, result, and
provenance. CPU operations are local and bounded; GPU execution requires detection or an
explicit mock backend; quantum simulation is deterministic and always labeled simulated.
Remote and physical QPUs are unavailable until an adapter is configured. Consequential
compute requires explicit human approval through the capability broker. No arbitrary code
execution is accepted as a compute operation.

Persistent Cognition stores every event in the durable SQLite event log, places it in a
priority-ranked attention queue, updates the Global Workspace when attended, and records
advisory outcomes. Reflection runs on a bounded background schedule and never executes
privileged actions. Duplicate memory consolidation is explicit and safe; failed skill
executions mark a skill for deliberate review rather than silently automating it.

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/message \
  -H 'Content-Type: application/json' \
  -d '{"text":"remember that the QPU is an accelerator, not a replacement for the CPU"}'
```

## Demonstrating Superconscious integration

Create a candidate skill:

```bash
curl -X POST http://127.0.0.1:8000/api/skills \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"ResearchSynthesis",
    "description":"Repeated research workflow",
    "trigger":"complex research request",
    "steps":["gather evidence","compare claims","verify","synthesize"]
  }'
```

Record three successful executions:

```bash
curl -X POST http://127.0.0.1:8000/api/skills/execute -H 'Content-Type: application/json' -d '{"name":"ResearchSynthesis","success":true}'
curl -X POST http://127.0.0.1:8000/api/skills/execute -H 'Content-Type: application/json' -d '{"name":"ResearchSynthesis","success":true}'
curl -X POST http://127.0.0.1:8000/api/skills/execute -H 'Content-Type: application/json' -d '{"name":"ResearchSynthesis","success":true}'
```

The skill becomes `integrated`. That is the MVP's concrete implementation of:

```text
deliberate workflow -> repetition -> validation -> integrated procedure
```

## Running tests

```bash
pip install -e '.[dev]'
pytest -q
ruff check acos tests
```

GitHub Actions runs these automatically on pushes and pull requests.

## Docker

```bash
docker build -t acos-hsc .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/app/data" acos-hsc
```

## Phone installation

When ACOS is served over HTTPS, open it in your phone browser and use **Add to Home Screen** / **Install App**. The included manifest and service worker make the UI a basic PWA.

For access to a home HSC over the internet, put ACOS behind a private VPN/tunnel such as WireGuard/Tailscale rather than exposing the development server directly. Add proper authentication before any remote deployment.

For v0.2 remote deployments, set `ACOS_REQUIRE_AUTH=true` and provide a high-entropy
`ACOS_API_TOKEN`. HTTP clients must send `Authorization: Bearer <token>`. WebSocket
clients may send the same header or use the `token` query parameter because browser
WebSocket APIs cannot set arbitrary headers. Authentication remains opt-in for local
development compatibility.

## Model Intelligence

Model Core uses the deterministic `mock` provider by default, so tests and local previews
work without network access. Configure an OpenAI-compatible local or hosted endpoint with
`ACOS_MODEL_PROVIDER`, `ACOS_MODEL_ENDPOINT`, `ACOS_MODEL_NAME`, and optionally
`ACOS_MODEL_API_KEY`. Requests include the current Global Workspace and retrieved memories.
Responses are typed safe outputs containing conclusions, confidence, evidence, assumptions,
uncertainty, and proposed actions; private chain-of-thought is never stored or streamed.
Timeouts and retries apply to the configured provider, with the deterministic mock as a
safe fallback. Model responses are recorded as safe `model.response` events and are delivered
to authenticated `/ws/events` clients. Proposed actions are advisory only: executable
actions still require registered capabilities and the existing human-approval checks.

## Roadmap

### 0.1 â€” included here
- memory
- workspace
- self-model
- task router
- skills
- permission broker
- Qiskit simulator
- PWA

### 0.2
- real authentication and device identities
- encrypted database / secrets management
- semantic/vector memory
- local or remote language-model provider interface
- structured planner and verifier

### 0.3
- GPU telemetry and job queue
- CUDA-Q adapter
- IBM Quantum physical-QPU adapter
- workload benchmarking and cost/latency routing

### 0.4
- multimodal sensor/event adapters
- explicit uncertainty/provenance graph
- sandboxed code-execution worker
- human-reviewed patch proposal pipeline

### 1.0 HSC layer
- heterogeneous scheduler for CPU/GPU/QPU
- hardware abstraction interfaces
- local-node + phone satellite identity model
- secure remote control plane
- real HSC hardware integration

## What this prototype is *not*

- It is not AGI.
- It does not prove machine subjective experience.
- It does not give an AI unrestricted control of the computer.
- It does not automatically rewrite itself.
- A Qiskit simulator is not a physical QPU.

### The World

Use `world`, `world status`, `advance time`, `create entity <name>`, and
`remember that ...` in chat. World operations are deterministic, bounded, local-only
SQLite writes: they cannot execute code, fetch videos, or create autonomous agents. The
conceptual inspiration includes information theory, transformer explanations, neural nets,
mathematical prediction, simulation hypotheses, and laboratory mini-universe/time
experiments; no runtime media retrieval or copyrighted transcription is used.

The goal is to build the **testable operating architecture first**, then replace individual subsystems as better AI and quantum hardware becomes available.
