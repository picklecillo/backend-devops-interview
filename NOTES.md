# Notes

## What I did and why

**Developer experience: Docker Compose dev environment**

- `Dockerfile`, `docker-compose.yml`, `docker/entrypoint.sh`: containerize the app and Postgres so `make up` is the whole setup step, replacing "install mise, install a local Postgres 16, create a database by hand" from the README.
- `core/settings.py`: DB config now reads `POSTGRES_*` env vars, falling back to the previous hardcoded `localhost`/`postgres`/`postgres` defaults — the existing host-based (`uv run ...`) workflow still works unchanged.
- Entrypoint only waits for the db and runs migrations, then starts the dev server. Seeding is a separate `make seed` target rather than baked into container startup, because the seed script takes a long time (see below) and shouldn't block `make up` / `make logs` from being usable.
- `Makefile`: `install` (bootstraps mise + uv for anyone not using Docker), `up`, `logs`, `down`, `seed`, `test` (`uv run pytest` on the host), `format` (`uv run ruff format .`).
- `pyproject.toml`: added `extend-exclude = ["*/migrations/*"]` to `[tool.ruff]` so `make format` doesn't rewrite Django-generated migration files.
- Ran `make format` and committed the result: `blog/apps.py`, `blog/tests/test_comments.py`, `core/asgi.py`, `core/wsgi.py`, `manage.py` predated ruff being wired up as a formatter here. Pure style (quote normalization, line wraps), no behavior change.
- Source is bind-mounted into the app container for hot reload; the container's `.venv` is a separate named volume so a host macOS `.venv` doesn't shadow the container's Linux one.

**Performance: N+1 queries and unbounded list_posts**

- `list_posts`, `search_posts`, `posts_by_tag`, and `get_post` (`blog/api.py`) all triggered a query per row: `post.author` and `post.tags.all()` per post, plus `comment.author` per comment in `get_post`. Added `select_related("author")` / `prefetch_related("tags")` (and `select_related("author")` on the comments queryset). Verified with `CaptureQueriesContext`: `list_posts` over ~90k published posts went from thousands of queries to 2; `get_post` on a post with 162 comments went from ~165 queries to 4.
- `list_posts` also returned every published post in a single response (90k+ rows serialized every call). Added simple page-number pagination, 100 per page, `?page=` query param, default `page=1`. Kept the existing plain-list response shape (rather than Ninja's built-in wrapping pagination) so the existing smoke test and any consumer expecting a bare array aren't broken.

## What I deliberately didn't do

- **Didn't touch the seed script.** `seed.py`'s comment-seeding loop calls `random.choices(post_ids, weights=post_weights, k=1)` once per comment (500k times) over a 100k-item weighted list — `random.choices` rebuilds cumulative weights on every call, making this effectively O(n·k), and seeding took well over an hour in my container instead of the "few minutes" the README suggests. This is a real perf bug but it's a one-time dev-setup cost, not a request-path issue, and the assignment scopes performance work at the API. Precomputing the cumulative weights once (`random.choices` accepts a `cum_weights` or you can roll your own bisect-based sampler) would fix it in a follow-up.
- **Didn't paginate `search_posts` or `posts_by_tag`.** They got the same select_related/prefetch_related fix since they share `_serialize_post_list`, but I didn't add pagination since it wasn't asked for and `posts_by_tag`/`search_posts` result sets are typically much smaller than the full post list — worth doing for consistency, but I prioritized depth on the one endpoint over breadth.
- **No production deployment target.** Ran out of time budget before getting to containerizing for prod / picking a deploy target (Helm, ECS, etc.). The Dockerfile as written is dev-oriented (bind mounts, `runserver`, `DEBUG=True` still in settings) and would need a separate prod image (gunicorn/uvicorn, `DEBUG=False`, secret management, static file serving) before it's suitable for that.
- **No auth/authz** and **no new test coverage**, per the README's non-goals.

## What I'd do next with another day

1. **Production readiness**, the area I didn't get to: multi-stage Dockerfile for a slim prod image, gunicorn instead of `runserver`, `DEBUG` / `SECRET_KEY` / `ALLOWED_HOSTS` driven from env with safe non-debug defaults, and a real deploy target (would reach for a plain ECS task def or a small Fly/Render config given the size of this service).
2. **Fix the seed script's O(n·k) weighted sampling** so local setup is actually fast, matching the README's stated "few minutes."
3. **Paginate `search_posts` and `posts_by_tag`** the same way as `list_posts`, and consider a full-text index (`SearchVector`/GIN or trigram) for `search_posts` instead of `icontains` over `title`/`body`, which is a sequential scan at this table size.
4. **Add DB indexes** — `Post.is_published` + `Post.created_at` are filtered/sorted on every list endpoint; a composite index would help once query counts are already fixed.
5. Wire the existing smoke tests into CI (mentioned as a non-goal to *write* new tests, but the README calls out that's what they're there for).

## AI usage

Done with Claude Code (Sonnet 5) as a pair-programming agent — it wrote the Docker/Makefile setup, diagnosed and fixed the N+1s (verified via query-count assertions against the live seeded container, not just code review), and added pagination. I directed scope and reviewed/tested each change against the running stack before moving on.
