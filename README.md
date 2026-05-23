# Smart Contract Auditor

Web app for **deep static, symbolic, and behavioral analysis of Solidity smart contracts**.

## Features

- **Multi-engine static analysis** — built-in heuristic detectors + [Slither](https://github.com/crytic/slither) + [Mythril](https://github.com/Consensys/mythril) symbolic execution
- **Mempool / MEV exposure** — slippage, sandwich, spot-price oracle, ERC-4626 inflation, approve-race
- **Honeypot scanner** — risk-scored 0-100 based on tax, blacklist, transfer-restriction, and rug patterns
- **Call graph visualization** — interactive react-flow viewer of contracts, inheritance, and call edges
- **Diff audit** — compare two contract versions, see introduced and fixed findings
- **Audit history** — SQLite-backed persistent runs with replay
- **AI-assisted explanations** per finding (Anthropic Claude / OpenAI)
- **On-chain fetch** — Etherscan, BscScan, Polygonscan, Arbiscan
- **Report export** — Markdown, JSON, **PDF**

## Architecture

```
┌─────────────────────────────┐    HTTP    ┌──────────────────────────┐
│  Next.js 14 + Tailwind      │ ─────────► │  FastAPI                 │
│  ├─ Audit page              │            │  ├─ /audit (full)        │
│  ├─ Diff audit              │            │  ├─ /honeypot            │
│  ├─ Call graph (react-flow) │            │  ├─ /graph               │
│  ├─ Honeypot scan           │            │  ├─ /diff/audit          │
│  └─ History                 │            │  ├─ /history             │
└─────────────────────────────┘            │  └─ /report (md/json/pdf)│
                                           │                          │
                                           │  Engines:                │
                                           │  ├─ custom_detectors     │
                                           │  ├─ mempool_detector     │
                                           │  ├─ honeypot_detector    │
                                           │  ├─ slither_runner       │
                                           │  ├─ mythril_runner       │
                                           │  ├─ call_graph           │
                                           │  ├─ diff_analyzer        │
                                           │  ├─ pdf_renderer (fpdf2) │
                                           │  └─ ai_explainer         │
                                           │                          │
                                           │  Storage: SQLite         │
                                           └──────────────────────────┘
```

## Built-in detectors (no external tool required)

### Custom (8 detectors)
| Detector | Severity |
|---|---|
| Reentrancy (state write after external call) | Critical |
| `tx.origin` for authorization | High |
| `selfdestruct` usage | High |
| Sensitive function w/o access control | High |
| Unchecked low-level call | Medium |
| Missing zero-address check | Medium |
| `block.timestamp` reliance | Low |
| Floating pragma | Informational |

### Mempool / MEV (6 detectors)
| Detector | Severity |
|---|---|
| Block-based pseudo-randomness | High |
| Spot-price oracle (sandwich) | High |
| Missing slippage protection | High |
| ERC-4626 first-depositor inflation | High |
| Front-runnable state mutation | Medium |
| ERC-20 approve race | Medium |

### Honeypot (9 indicators)
Sender-restricted transfer (only-owner-sells), high tax, owner-modifiable tax,
blacklist mechanism, owner-controlled trading pause, uncapped mint, fake renounce,
owner balance override, owner-controlled max-tx.

> Slither adds 80+ additional detectors when available. Mythril adds symbolic
> execution discovery of unreachable bugs.

## Quick Start

### Docker (recommended)
```bash
git clone https://github.com/Zerxxz/Smart-contract-analyst-tool.git
cd Smart-contract-analyst-tool
cp backend/.env.example backend/.env   # fill in API keys (optional)
docker compose up --build
```
Open http://localhost:3000

### Local dev
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## API surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/audit/source` | POST | Full audit on raw Solidity |
| `/audit/address` | POST | Full audit by on-chain address |
| `/audit/health` | GET | Slither/Mythril availability + detector list |
| `/honeypot/source` | POST | Risk-scored honeypot report |
| `/honeypot/address` | POST | Same, by address |
| `/graph/source` | POST | Call graph (nodes + edges) |
| `/graph/address` | POST | Same, by address |
| `/diff/audit` | POST | Compare two contract versions |
| `/history` | GET | List saved audits |
| `/history/{id}` | GET / DELETE | Detail view / delete |
| `/report/export` | POST | Export as `markdown`, `json`, or `pdf` |

Interactive docs: `http://localhost:8000/docs`

## Configuration

`backend/.env`:
```env
# Block explorers
ETHERSCAN_API_KEY=
BSCSCAN_API_KEY=
POLYGONSCAN_API_KEY=
ARBISCAN_API_KEY=

# AI provider — pick one
AI_PROVIDER=anthropic          # anthropic | openai | minimax | none
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# MiniMax (https://platform.minimax.io)
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/v1/text/chatcompletion_v2
MINIMAX_MODEL=MiniMax-M2.7

# CORS / DB
FRONTEND_ORIGIN=http://localhost:3000
AUDIT_DB_PATH=/app/data/audit_history.db
```

### Choosing an AI provider

| Provider | Default model | Get a key at |
|---|---|---|
| `anthropic` | `claude-3-5-sonnet-20241022` | https://console.anthropic.com |
| `openai` | `gpt-4o-mini` | https://platform.openai.com |
| `minimax` | `MiniMax-M2.7` | https://platform.minimax.io |

If no provider is configured (`AI_PROVIDER=none` or no key), the audit
report is still produced via a deterministic templated synthesis — the
response shape is identical, only the narrative prose and AI-suggested
patches are absent.

## Roadmap

- [ ] Echidna fuzzing integration
- [ ] Token-specific live simulation (fork-based honeypot test)
- [ ] Multi-file project upload (Foundry/Hardhat)
- [ ] Persistent diff against on-chain deployments
- [ ] WebSocket live audit progress
- [ ] Mempool monitoring (real-time mempool exposure analysis on live RPCs)

## License

MIT
