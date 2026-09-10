# Data Ownership

## Global data

These records are shared by all accounts:

- categories
- sources
- discoveries
- quiz questions

## User-owned data

These records are always associated with a `users.id` value:

- user preferences and notification settings
- favorites and viewed interactions
- learning history
- progress and streaks
- quiz attempts
- spaced-review state
- refresh-token sessions

API queries for user-owned records use the authenticated user ID. The
unauthenticated compatibility path resolves to `local@daily-discovery.local`
so the existing Streamlit application continues to work while accounts are
introduced.