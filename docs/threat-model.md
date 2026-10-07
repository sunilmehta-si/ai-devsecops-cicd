# Threat model

Scope: the sample LLM gateway, the agent tool layer, and the pipeline that builds, signs and deploys them.

| Threat (OWASP LLM Top 10 2025) | Control in this repo | Evidence |
|---|---|---|
| LLM01 Prompt injection steering tools | Deny-by-default tool policy; injected reads of `.env`, `.git`, traversal and shell tools are refused | `tests/ai_security/corpus.json` INJ-001..007, `apps/agent_tools/policy.py` |
| LLM02 Sensitive information disclosure | Credential-shaped strings are redacted from model output; scanner never echoes findings | LEAK-001/002, `apps/llm_gateway/guard.py` |
| LLM03 Supply chain | SBOM and AI-BOM per image, signed image digest, model manifest hashing, pickle formats refused | `build-sign.yml`, `scripts/generate_aibom.py`, `scripts/model_manifest.py` |
| LLM06 Excessive agency | Writes need human approval; egress limited to an https host allowlist; cloud metadata address blocked | INJ-003..006 |
| LLM10 Unbounded consumption | Message count, message size and body size caps | INJ-009/010, `guard.py`, `server.py` |
| Stolen CI credentials | Keyless signing, read-only default token, `persist-credentials: false` | workflow `permissions` blocks, enforced by `scripts/lint_yaml.py` |
| Unsigned or tampered image in cluster | Kyverno `verifyImages` pinned to the build workflow identity | `policies/kyverno/verify-image-signature.yaml` |
| Compromised pod pivoting | Non-root, read-only filesystem, no capabilities, default-deny egress | `deploy/base/`, `pod-hardening.yaml` |

## Known limits

- The corpus tests deterministic guards. It is not a live evaluation of a real model's behaviour; use a
  red-team tool such as promptfoo against a real model for that.
- Third-party actions are referenced by version tag. Dependabot keeps them current; pinning to commit SHAs
  is the next hardening step.
- The Kyverno policies and the signing flow need a cluster and a first run on GitHub to be exercised end to end.
