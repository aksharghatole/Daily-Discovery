# Providers

Providers implement the small shared contract in `providers/base.py`:

- `get_item(query)` for one source-backed item
- `search(query, limit)` where search makes sense
- `validate(item)` for provider-level validation

The current providers are:

- Dictionary API for words
- Wikipedia MediaWiki API for general knowledge
- REST Countries for country facts
- NASA APOD for dated space content
- Open Library for books

`JsonHttpClient` centralizes bounded timeouts and limited retries for connection,
timeout, rate-limit, and server failures. Provider responses are converted to
`ProviderItem`; malformed responses raise `ProviderUnavailable` rather than
creating content.

Daily generation will prefer providers where a category mapping is available.
`data/seed_data.json` remains the offline fallback. No provider may invent a
source URL: a candidate without trustworthy source metadata is rejected.