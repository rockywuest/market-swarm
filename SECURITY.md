# Security Policy

## Reporting vulnerabilities

Please report security vulnerabilities **privately** via GitHub's Security Advisory feature:

1. Go to the [Security tab](https://github.com/rockywuest/market-swarm/security)
2. Click "Report a vulnerability"
3. Describe the issue, its impact, and any proof-of-concept

We'll respond within 48 hours. Do not open public issues for security vulnerabilities.

## Supported versions

Only the **latest version on `main`** receives security updates.

## Important: data handling in simulations

Market Swarm sends your product YAML to the LLM provider you configure (Gemini, Anthropic, OpenRouter, or OpenAI). **Never include trade secrets, real company data, or identifiable information in your product definitions.**

The product YAML is the only data sent to cloud LLM APIs. All persona text, evaluation logic and results processing stay local.

If you're running simulations with sensitive product data:
- Use a private LLM provider (self-hosted Ollama, on-prem Claude models, private OpenRouter keys)
- Anonymize product names and competitor references
- Verify your LLM provider's data retention and compliance policies

## Scope

This project covers simulation and reporting logic. Security issues outside scope:

- Vulnerabilities in upstream LLM providers (report directly to them)
- Vulnerabilities in your LLM key management (use environment variables, never hardcode)
- Issues with third-party package dependencies (report to the maintainers; we'll update pinned versions)

## Compliance notes

- **EU AI Act Art. 50:** Every output carries an AI-generation disclaimer
- **GDPR:** Product YAML data handling is transparent; no hidden data flows
- **Python version:** We support Python 3.11+ with regular dependency updates

## What we will not do

- Support end-of-life Python versions
- Guarantee backward compatibility across major versions
- Review your LLM provider's terms; that's your responsibility
