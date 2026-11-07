# AI Provider Configuration & Cost Management

Nexora implements a dual-tier AI architecture with automatic fallback, multi-provider model routing, token-level cost tracking, and budget enforcement.

---

## 1. Dual-Provider Architecture

```
User Action / Service Request
           │
           ▼
┌─────────────────────────────────┐
│     Central AI Provider Factory │
└─────────────────────────────────┘
           │
           ├── Check Primary Provider (OpenAI)
           │     ├── Configured & Healthy? ──► Execute Model Tier
           │     └── Unconfigured / Error? ──► Trigger Secondary Fallback
           │
           ├── Check Secondary Provider (Google Gemini)
           │     ├── Configured & Healthy? ──► Execute Model Tier
           │     └── Unconfigured / Error? ──► Deterministic Rule Fallback
           │
           └── Fallback: Deterministic Rule Engine (No AI token cost)
```

### 1.1 Provider Tiers
- **Primary Provider**: **OpenAI**
  - **Routine Tier**: `gpt-4o-mini` ($0.150 / 1M prompt tokens, $0.600 / 1M completion tokens). Used for resume parsing, keyword extraction, and simple classification.
  - **Strong Tier**: `gpt-4o` ($2.50 / 1M prompt tokens, $10.00 / 1M completion tokens). Used for resume tailoring, multi-step interview simulations, and recruiter outreach composition.
- **Secondary Provider**: **Google Gemini**
  - **Routine Tier**: `gemini-2.5-flash` ($0.075 / 1M prompt tokens, $0.300 / 1M completion tokens). High-speed analysis and classification.
  - **Strong Tier**: `gemini-1.5-pro` ($1.25 / 1M prompt tokens, $5.00 / 1M completion tokens). Complex multi-document synthesis and long-context evaluations.

---

## 2. Server-Side Budget Guardrails & Cost Tracking

### 2.1 The `AIUsageLog` Audit Entity
Every external AI call is recorded in the `ai_usage_logs` table:
- `user_id`: Attributed user (or system task).
- `provider`: Provider invoked (`openai`, `gemini`).
- `model`: Exact model identifier.
- `feature`: Domain feature (`resume_tailor`, `cover_letter`, `interview_prep`, `copilot`).
- `prompt_tokens`, `completion_tokens`, `total_tokens`.
- `estimated_cost_usd`: Calculated based on published token prices.
- `latency_ms`: Round-trip execution latency.
- `cache_hit`: Boolean flag indicating if cached result was served.

### 2.2 Cost Manager Enforcement (`AICostManager`)
Before dispatching a generation request, `AICostManager.check_limits_and_cache()` verifies:
1. **Daily Platform Ceiling**: Rejects if today's platform spend exceeds `AI_DAILY_BUDGET_USD` ($10.00/day).
2. **Monthly Platform Ceiling**: Rejects if the calendar month platform spend exceeds `AI_MONTHLY_BUDGET_USD` ($100.00/month).
3. **Per-User Daily Quota**: Rejects if user's daily tokens exceed `AI_USER_DAILY_TOKEN_LIMIT` (150,000 tokens) or daily cost exceeds `AI_USER_DAILY_BUDGET_USD` ($2.00).
4. **Duplicate Request Fingerprinting**: Calculates SHA-256 of `(user_id, feature, model, prompt_text)`. If found in Redis or memory within 24 hours (`AI_RESPONSE_CACHE_TTL_SECONDS`), returns the cached response instantly with zero API cost and `cache_hit: true`.

---

## 3. Disclaimers & Invoice Variance
All AI cost reporting endpoints and user-facing dashboards display the following mandatory disclaimer:
> *"Estimated cost computed from token consumption and published provider rates. Actual provider invoices may vary depending on taxes, discounts, enterprise tiers, or rounding policies."*

