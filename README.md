# StrategyPilot AI

StrategyPilot AI turns raw trading-result CSV data into deterministic performance evidence, prioritized engineering tasks, and regression checks. It is an engineering audit tool—not financial advice, a trading signal, or a prediction system.

Built as an OpenAI Build Week 2026 submission, the MVP is intentionally submission-ready and narrow: local CSV input, transparent Python calculations, an interactive Streamlit dashboard, evidence-grounded GPT-5.6 findings, and a Markdown export.

## Problem

Trading-system experiment exports often mix partial exits, inconsistent labels, and raw trade legs. A naive dashboard can count TP1 and TP2 as separate wins, inflate sample size, and then ask an AI model to reason over unverified rows. That produces weak engineering decisions and statistics that are difficult to reproduce.

## Solution

StrategyPilot validates and normalizes the CSV, reconstructs each complete `setup_id`, calculates every statistic deterministically in Python, and only then builds a compact aggregate evidence payload. GPT-5.6 can interpret that evidence into engineering work, but it never calculates dashboard metrics and never receives raw trades.

## Features

- Included multi-leg sample data and CSV upload workflow
- Canonical schema validation, aliases, type coercion, and readable errors
- Correct setup reconstruction before counts, win rate, or performance metrics
- Eleven deterministic performance metrics plus direction and session slices
- Interactive equity, drawdown, distribution, direction, and session charts
- Evidence ledger that makes setup aggregation inspectable
- Structured GPT-5.6 engineering findings through the Responses API
- Verified evidence-key rendering that prevents model-authored statistics
- Fully functional deterministic Demo Audit without an API key
- Downloadable Markdown audit and a clear financial-information disclaimer

## Architecture

```text
CSV / sample
    │
    ▼
src/parser.py       validate + normalize canonical rows
    │
    ▼
src/metrics.py      reconstruct setup_id → deterministic metrics
    ├── src/charts.py    Plotly figures
    ├── evidence table   inspectable setup ledger
    └── src/audit.py     compact aggregate JSON → GPT-5.6 or demo rules
                              │
                              ▼
                         structured findings
                              │
                              ▼
                       Markdown export
```

`app.py` owns the Streamlit presentation and state. `src/utils.py` owns display and export formatting. There is no database, authentication, broker integration, proprietary strategy logic, or live-trading path.

## Deterministic calculations vs. AI interpretation

All statistics are calculated with pandas after rows sharing a `setup_id` are aggregated. A setup is a win only when its combined P&L is positive; zero is breakeven. Gross loss is reported as a positive magnitude. Drawdown is the absolute worst decline from a running equity peak, with initial capital normalized to zero.

The model receives only JSON containing the verified overview, direction groups, and session groups. It returns finding prose plus references to allowed evidence keys. StrategyPilot renders the corresponding evidence labels and values itself. If the API fails validation, the app falls back to its deterministic Demo Audit rather than displaying untrusted statistics.

## How GPT-5.6 is used

The OpenAI Python SDK calls the Responses API with `gpt-5.6-sol` by default, low reasoning effort, low text verbosity, and a strict JSON Schema. The model produces three to five findings containing a finding, evidence-key references, an engineering task, a regression check, and a High/Medium/Low priority. Its prompt prohibits trading recommendations, predictions, calculations, and numeric prose.

Set `OPENAI_MODEL` to override the default when evaluating another compatible model. The explicit Sol default matches this audit's quality-first, low-volume role.

## How Codex was used

Codex acted as the principal build agent for the local MVP: repository inspection, architecture, setup-level metric implementation, Streamlit interface, sample fixture, tests, documentation, and local validation. The build kept deterministic calculations separate from model interpretation and followed official OpenAI Responses API/model guidance. The release was validated locally before publication.

## Local setup

Requirements: Windows or another Python-capable OS, Python 3.10+, and a virtual environment.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Environment variables

PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-5.6-sol"
```

Alternatively, create `.streamlit/secrets.toml` (do not commit it):

```toml
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "gpt-5.6-sol"
```

`OPENAI_API_KEY` is optional. Without it, the complete dashboard and a clearly labeled deterministic Demo Audit remain available. Secrets are read at runtime and are never displayed or logged.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Run Streamlit

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open the local URL shown by Streamlit, normally `http://localhost:8501`.

## Deployment

For Streamlit Community Cloud:

1. Review and push the repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository and select `app.py`.
3. Set Python to a compatible 3.10+ runtime.
4. Add `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the app's Secrets settings.
5. Deploy and verify both the included-sample path and a CSV upload.

The app also deploys without an API key; it will use deterministic Demo Audit mode.

## CSV schema

| Column | Required | Type / behavior |
|---|---:|---|
| `trade_id` | No | Unique trade-leg identifier; generated when missing |
| `setup_id` | No | Complete setup identifier; falls back to `trade_id` |
| `entry_time` | Yes | Datetime parseable by pandas; normalized to UTC |
| `direction` | Yes | `long`/`short`; `buy`/`sell` aliases accepted |
| `pnl` | Yes | Numeric realized P&L for the row |
| `session` | No | Group label; defaults to `Unknown` |
| `symbol` | No | Instrument label; defaults to `Unknown` |
| `exit_reason` | No | Exit label; defaults to `Unknown` |
| `mae` | No | Numeric maximum adverse excursion |
| `mfe` | No | Numeric maximum favorable excursion |

Header aliases include `timestamp` → `entry_time`, `side` → `direction`, `profit_loss` → `pnl`, and `ticker` → `symbol`. Extra columns are ignored with a warning. For multi-leg exits, every leg must share the same `setup_id`.

## Demo workflow

1. Run Streamlit; the included sample is selected by default.
2. Review the validation confirmation and reconstructed setup count.
3. Inspect deterministic metric cards and interactive charts.
4. Open the evidence table and reconstructed setup ledger.
5. Review the AI Audit when a key is configured, or the labeled Demo Audit otherwise.
6. Download the audit as Markdown.
7. Switch to **Upload CSV** to validate another result set.

## Limitations

- Results are only as reliable as the supplied P&L and `setup_id` mapping.
- Currency formatting assumes the P&L unit is monetary and shared across rows; no FX conversion is performed.
- A setup containing conflicting directions, sessions, or symbols is labeled `Mixed`.
- MAE and MFE are normalized but not yet included in MVP metrics.
- The app does not infer fees, slippage, starting capital, exposure, or unrealized P&L.
- No model output can establish future profitability; findings are engineering hypotheses to test.
- Live API behavior depends on account access, quotas, model availability, and network connectivity.

## Financial disclaimer

StrategyPilot AI is for informational, software-engineering, and historical-test analysis purposes only. It is not financial, investment, legal, or tax advice; it does not recommend trades; and it does not predict future performance. Historical or simulated results do not guarantee future results.

## OpenAI Build Week 2026

This public-repository MVP demonstrates a disciplined pattern for AI-assisted engineering: calculate evidence deterministically, expose the calculation boundary, pass only verified aggregates to the model, constrain the output contract, and make every recommendation testable.

## License

MIT — see [LICENSE](LICENSE).
