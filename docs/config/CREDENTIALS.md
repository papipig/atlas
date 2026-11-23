# Credentials and Secret Handling

This project separates business configuration from secrets.

## Principles
- Never commit raw secrets to the repository.
- Store only credential references in database records.
- Resolve secret values at runtime from environment variables or a secret manager.
- Log credential reference changes in audit logs.

## How Source Auth Works
Each source can define:
- auth_mode: none | api_key | oauth2 | basic | cookie
- credential_ref: optional reference id (for protected sources)

At runtime:
1. Worker reads source.credential_ref.
2. Worker loads mapped secret names for this credential ref.
3. Worker fetches secret values from selected backend.
4. Worker builds authenticated request.

## Local Development
Use .env (gitignored) or docker env files for real secret values.

Expected pattern:
- CREDENTIALS_BACKEND=env
- CREDENTIALS_PREFIX=ATLAS_CRED_

## Production (VPS)
Use one of:
- Injected environment variables from deployment pipeline
- Dedicated secret manager

Recommended controls:
- Key rotation policy
- Least privilege API scopes
- Service accounts instead of personal accounts
- Audit trail for any credential mapping change

## Example Catalog
See docs/config/credentials-store.example.json for a reference-only credential catalog structure.
