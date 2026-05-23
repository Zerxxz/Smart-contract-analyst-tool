# Smart Contract Auditor

A web app for **deep static analysis & audit of Solidity smart contracts**.

## Features (MVP)

- Paste Solidity source **or** fetch verified source from an on-chain address
- Runs **custom heuristic detectors** (always available, pure Python)
- Optional **Slither** integration (industry-grade static analyzer)
- Optional **AI-assisted explanation** per finding (Anthropic Claude / OpenAI)
- **Severity-sorted findings** with code snippets and line markers
- **Markdown / JSON report export**
- Multi-chain explorer support: Ethereum, BSC, Polygon, Arbitrum

## Architecture

```
┌──────────────────┐     HTTP     ┌────────────────────┐
│  Next.js 14      │ ───────────► │  FastAPI           │
│  Tailwind +      │              │  ├ custom detectors│
│  Monaco Editor   │              │  ├ slither runner  │
└──────────────────┘              │  ├ AI explainer    │
                                  │  └ etherscan fetch │
                                  └────────────────────┘
```

## Built-in Custom Detectors

| Detector | Severity |
|---|---|
| `tx.origin` for authorization | High |
| Unchecked low-level call | Medium |
| Reentrancy pattern (state write after external call) | Critical |
| Floating pragma | Informational |
| Reliance on `block.timestamp` | Low |
| Use of `selfdestruct` | High |
| Missing zero-address check | Medium |
| Sensitive function lacks access control | High |

> Slither adds 80+ additional detectors when available.

## Quick Start

### Option A — Docker (recommended)

```bash
cd smart-contract-auditor
cp backend/.env.example backend/.env   # fill in API keys (optional)
docker compose up --build
```

Open http://localhost:3000

### Option B — Local dev

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend (in another terminal):**
```bash
cd frontend
npm install
npm run dev
```

## API

- `POST /audit/source` — audit raw Solidity source
- `POST /audit/address` — audit verified contract by address
- `POST /report/export` — export report as Markdown or JSON
- `GET  /audit/health` — backend status (slither availability, detectors)

Interactive docs: `http://localhost:8000/docs`

## Configuration

Edit `backend/.env`:

```env
ETHERSCAN_API_KEY=...
BSCSCAN_API_KEY=...
POLYGONSCAN_API_KEY=...
ARBISCAN_API_KEY=...

AI_PROVIDER=anthropic      # or openai or none
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

## Roadmap

- [ ] Mythril symbolic execution
- [ ] Echidna fuzzing integration
- [ ] Call graph & inheritance visualization
- [ ] Token-specific checks (honeypot, rug-pull patterns)
- [ ] Diff-based audit (compare two contract versions)
- [ ] Persistent history with SQLite
- [ ] PDF export
- [ ] Mempool monitoring (real-time mempool exposure analysis)

## License

MIT
