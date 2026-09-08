# Architecture

```text
Teller camera client
        |
        | X-Bank-Code + X-API-Key + PC name + cropped image
        v
FastAPI ingestion and DeepFace analysis
        |-- authenticates the bank
        |-- resolves the branch from the longest matching PC prefix
        |-- validates and stores the private image
        |-- detects expression and matches a tenant-scoped visitor
        `-- writes analytics to Supabase PostgreSQL
                              |
                              v
Django SaaS dashboard and admin
        |-- platform superuser access
        |-- bank administrator access
        |-- branch user access
        `-- tenant-filtered visitors, history, reports, and settings
```

## Ownership boundaries

- Django migrations own the relational schema.
- Supabase PostgreSQL is the authoritative shared data store.
- FastAPI authenticates ingestion and performs analysis synchronously.
- The teller client never selects a branch; its Windows PC name determines it.
- Captured files are private server-side data. Django serves them only through
  an authenticated, tenant-authorized view.
- One-host development can use the shared local `captured_faces` directory;
  multi-host production needs private object storage.

## Tenant model

A `Bank` is the top-level SaaS tenant and owns branches, visitors, snapshots,
settings, and an upload-key hash. A bank administrator can see every branch of
their bank. A branch user is restricted to their assigned branch. A platform
superuser can administer every tenant.
