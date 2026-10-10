# AI DevSecOps CI/CD

[![ci](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/ci.yml/badge.svg)](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/ci.yml) [![security-scan](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/security.yml/badge.svg)](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/security.yml) [![ai-security](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/ai-security.yml/badge.svg)](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/ai-security.yml) [![build-scan-sign](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/build-sign.yml/badge.svg)](https://github.com/sunilmehta-si/ai-devsecops-cicd/actions/workflows/build-sign.yml)

A reference pipeline for shipping LLM and AI-agent services safely: **scan, test, sign, gate, deploy**.
Built by [Sunil Mehta](https://github.com/sunilmehta-si) as a companion to
[llm-inference-platform](https://github.com/sunilmehta-si/llm-inference-platform),
[jev-inference-router](https://github.com/sunilmehta-si/jev-inference-router) and
[agentic-code-review-tool](https://github.com/sunilmehta-si/agentic-code-review-tool), which reviews pull requests
for the same classes of risk this pipeline blocks.

The point is the pipeline, not the app. A small dependency-free gateway and agent tool layer give the
controls something real to protect.

## Pipeline

```mermaid
flowchart TB
    dev[Developer commit] --> hook[pre-commit secret scan]
    hook --> pr[Push / pull request]
    pr --> ci[ci.yml<br/>tests · history secret scan<br/>YAML + permission lint · manifest rules]
    pr --> sec[security.yml<br/>Gitleaks · Semgrep SARIF · Trivy config]
    pr --> ai[ai-security.yml<br/>OWASP LLM injection + leakage corpus<br/>gateway auth smoke test]
    ci & sec & ai --> main[Merge to main]
    main --> build[build-sign.yml]
    subgraph supply[Supply chain on main]
        build --> scan[Trivy image scan<br/>blocks HIGH/CRITICAL]
        scan --> bom[SBOM + AI-BOM]
        bom --> sign[Keyless cosign sign + attest]
        sign --> verify[Verify signature<br/>against this workflow]
    end
    verify --> argo[Argo CD GitOps sync<br/>self-heal]
    argo --> kyverno{Kyverno admission}
    kyverno -->|signed, hardened, trusted registry| run[Running in cluster]
    kyverno -->|anything else| deny[Rejected]
```

Every workflow runs with a least-privilege token, and every action is pinned to a full commit SHA that Dependabot keeps current.

## What is in the box

| Area | Files |
|---|---|
| Secret safety | `.gitignore`, `scripts/check_secrets.py`, `.githooks/pre-commit`, `SECURITY.md` |
| Sample LLM gateway | `apps/llm_gateway/` (auth, validation, output redaction) |
| Agent tool controls | `apps/agent_tools/` (deny-by-default policy, approval for writes, egress allowlist) |
| AI security tests | `tests/ai_security/corpus.json`, `scripts/run_ai_security.py` (14 cases, includes benign controls) |
| Model supply chain | `models.yaml`, `scripts/generate_aibom.py` (CycloneDX 1.6), `scripts/model_manifest.py` |
| CI/CD | `.github/workflows/` (four workflows, least-privilege tokens, keyless signing) |
| Admission policy | `policies/kyverno/`, offline mirror in `scripts/validate_manifests.py` |
| Deploy | `deploy/base/` (kustomize), `deploy/argocd/` |
| Threat model | `docs/threat-model.md` |

## Run it locally

```sh
make hooks     # enable the pre-commit secret scan
make verify    # unit tests, working-tree + history secret scan, YAML lint
python3 scripts/run_ai_security.py
python3 scripts/validate_manifests.py
```

Python 3.10+ and PyYAML are the only requirements. No GPU, API key or cloud account is needed.

## Honest status

- Verified locally: unit tests, the AI security corpus, manifest validation, YAML lint and a secret scan of
  every commit.
- Verified in GitHub Actions: all four workflows pass on `main`, including the image build, Trivy scan,
  SBOM and AI-BOM generation, keyless cosign signing and signature verification.
- Written but not yet exercised: the Kyverno policies need a cluster. The offline validator mirrors them
  and runs in CI, but admission-time enforcement has not been tested against a live API server.
- Limits and next steps are listed in [docs/threat-model.md](docs/threat-model.md).
