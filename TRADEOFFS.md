# Engineering Trade-offs & Deferred Features

To deliver a high-quality, defensible application within 4 days, feature scope was trimmed to focus heavily on data safety and analytical validation workflows.

## Deliberately Omitted Modules

### 1. Live Production OAuth Connections (Concur/Navan)
* **Rationale:** Integrating with actual Concur production environments requires sandboxed OAuth credential provisioning, client secrets, and enterprise compliance approvals. 
* **Trade-off:** We fully modeled the JSON data contract instead. This allowed us to build the normalization logic and exception handling engine without getting bottlenecked by external authentication infrastructure.

### 2. Asynchronous PDF Parsing (OCR Pipelines)
* **Rationale:** Processing mixed facility utility bills in PDF format requires complex vision models or layout-dependent parsing scripts (e.g., AWS Textract). These models are prone to structural errors when utility formats change.
* **Trade-off:** We restricted utility ingestion to standardized portal CSV exports. This ensures 100% precision for numeric metrics and avoids processing bugs during short timeline evaluations.

### 3. Live Global Grid Intensity API Lookups
* **Rationale:** Real-time greenhouse gas intensity changes based on grid demand and regional generation mixes (e.g., using Electricity Maps API integrations).
* **Trade-off:** We utilized localized static emission coefficients (e.g., 0.85 kg CO2e/kWh for regional grid averages). The codebase contains clear hooks so these numbers can be easily swapped for dynamic API inputs down the road without changing the underlying schema.