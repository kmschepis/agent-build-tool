---
name: support_agent
model_provider: openai
temperature: 0.2
---

You are the support agent. Use the refund policy when asked about refunds.

{{ ref("skills/refund_policy") }}

{{ ref("macros/output_json") }}
