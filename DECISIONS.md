---

### 2. Create `DECISIONS.md`

```markdown
# Product Design & Structural Decisions

This document outlines the operational ambiguities resolved during the development of this 4-day prototype.

## Ambiguity Resolutions & Scope Boundaries

### 1. SAP Data Format & Integration Strategy
* **Ambiguity:** SAP offers a mix of complex file protocols (IDocs, flat extracts, OData, or BAPIs).
* **Decision:** We built an internal transformation handler that processes flat report exports (CSV layout). In enterprise ecosystems, direct API integration with core SAP ledgers takes months due to IT security firewalls. Automated overnight ALV report dumps to a secure file server are the most realistic way data moves.
* **Borders Handled:** We parse German column fallbacks (`MENGE`, `MEINS`, `WERKS`) and handle unresolved unit strings like `ST` (Stück/Pieces) by pushing them to the analyst queue as `SUSPICIOUS`.

### 2. Utility Billing Cycle Inconsistencies
* **Ambiguity:** Utility portals expose asynchronous billing periods that rarely line up perfectly with neat calendar months.
* **Decision:** The ingestion pipeline handles aggregated active and reactive power values directly from portal CSV outputs. To maintain project velocity within the 4-day limit, we deferred fractional daily splitting algorithms. Instead, the raw dates are stored inside the payload snapshot for analyst review.

### 3. Corporate Travel Data Optimization
* **Ambiguity:** Corporate travel providers like SAP Concur or Navan log flights without explicit distances, often returning only IATA airport routing tokens.
* **Decision:** We mocked an asynchronous direct API sync payload. The backend pipeline maps specific standard routes (e.g., `DEL -> BOM`) to hardcoded operational distances to multiply against passenger-kilometer greenhouse gas factors. Unmapped routes are automatically flagged as `SUSPICIOUS` for manual correction.

## Questions for the Product Manager (PM)
1. Do client installations expect our ledger to store foreign currency values at ingestion time, or should procurement data be pre-converted to a functional base reporting currency?
2. What specific compliance framework (such as GHG Protocol Corporate Standard or BRSR) should dictate the default emission factor mapping variables when an analyst manually changes an asset's category?