# Scheduler

The scheduler is an APScheduler-backed standalone process. It calls the
generation orchestrator at
`00:05` in the configured application timezone. The generation service remains
callable independently for tests, manual runs, and recovery. A database-backed
generation record prevents concurrent jobs for the same calendar date.

Start it with:

```bash
python -m scheduler
```

The scheduler does not assume the server timezone is the application timezone.
It retries only incomplete categories after partial runs, and it avoids
regenerating categories already stored successfully for that date.