# Authentication

The FastAPI backend supports email/password accounts with Argon2 password
hashing, short-lived JWT access tokens, and revocable refresh-token sessions.

## Configuration

Set these values in `.env` for a deployed environment:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
```

`JWT_SECRET_KEY` must be unique and must not use the development fallback.
Never commit `.env` or production secrets.

## Endpoints

- `POST /api/auth/register` creates an account and returns an access/refresh pair.
- `POST /api/auth/login` authenticates an account and creates a device session.
- `POST /api/auth/refresh` rotates an active refresh token.
- `POST /api/auth/logout` revokes the supplied refresh token.
- `GET /api/auth/me` returns the authenticated account.
- `POST /api/auth/change-password` changes the password and revokes sessions.

Send access tokens as `Authorization: Bearer <token>`. User-owned API routes
use that account when a token is supplied. Anonymous requests remain supported
for the legacy local Streamlit workflow and use the compatibility local user.