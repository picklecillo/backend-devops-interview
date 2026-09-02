# Notes

## What I did and why

**Developer experience: local env setup**

* Created a Makefile for improved DX. There's `install` (bootstraps mise + uv for anyone not using Docker), `up`, `logs`, `down`, `seed`, `test` (`uv run pytest` on the host), `format` (`uv run ruff format .`).
* Containerized th app and db so `make up` is the only step needed to get the local environment ready.
* Improved the speed of the db seed command so it takes way less time (`make seed`).
* Source is bind-mounted into the app container for hot reload; the container's `.venv` is a separate named volume so a host macOS `.venv` doesn't shadow the container's Linux one.
* Set up `django-environ` so all secrets and config are loaded from a local (unstaged) `.env` file. There's a `.env.example` for reference. `docker-compose.yml` loads both services with `env_file: .env` + an explicit `POSTGRES_HOST: db` override on `app` since the container needs the compose service name, not `localhost`.
* Set up `django-debug-toolbar`: app, middleware, and urls only load when `DEBUG=True` (`core/settings.py`, `core/urls.py`) so it can never ship in a non-debug deployment. `SHOW_TOOLBAR_CALLBACK` bypasses the `INTERNAL_IPS` check since Docker's client IP isn't `127.0.0.1`; `UPDATE_ON_FETCH` registers fetch/XHR calls (e.g. from the `/api/docs` Swagger UI) in the toolbar's request history.
* Fixed `seed.py`'s comment-seeding loop calling `random.choices(post_ids, weights=post_weights, k=1)` once per comment (500k times) over a 100k-item weighted list, and similarly once per post for author selection. Fixed by generating all the weighted samples in a single call before any loop, instead of once for each row.

**Architecture: a service layer**

* Introduced a service layer so that api endpoints call a specific service method instead of directly interacting with the ORM. This may look like an early optimization right now, but it makes things easier when there's multiple apps that need other apps' logic. This way, for instance, there's a single place where a Post is created. If any other app needs to create a Post, that's the only point of contact. Also, side effects like enqueuing a notification can go on that same method. This also allows the bulk of the unit testing to go on the service methods and not the views (less mocking, no auth needed, etc)
* Note, thin views and a service layer is a personal preference but, while there's other ways code could be structured, this is one I've found produces less friction when there's multiple teams that own different apps on the same codebase, is very DRY and abstracts away the logic so there's less cognitive load when working with unfamiliar apps.

**Performance: N+1 queries and unbounded list_posts**

* `list_posts`, `search_posts`, `posts_by_tag`, and `get_post` (`blog/api.py`) all triggered a query per row: `post.author` and `post.tags.all()` per post, plus `comment.author` per comment in `get_post`. Added `select_related("author")` / `prefetch_related("tags")` (and `select_related("author")` on the comments queryset). As an example, `list_posts` over ~90k published posts went from thousands of queries to 2.
* Set up pagination (set default to 100) for `list_posts`, `search_posts` and `posts_by_tag`.

**Production readiness: Fly.io deployment**

* Configured the project to be deployed to Fly.io. Set up two separate Fly apps and Dockerfiles, one at the root and another at `/db/` for a self-managed postgres instance.
* `Dockerfile.fly`: built without dev dependencies (`UV_NO_DEV=1`), runs `collectstatic` at build time, serves via `gunicorn core.wsgi:application`. 
* No entrypoint script — `release_command` in `fly.toml` runs migrations in a temporary Fly machine before the new version goes live, so the running app process never runs `migrate` itself.
* Added a `/healthz` endpoint to ensure DB connectivity for use as the `http_service` check in `fly.toml`.
* Set up `whitenoise` + `gunicorn` added as real (non-dev) dependencies. `STORAGES`/`MIDDLEWARE` only switch to whitenoise's manifest-based static serving when `DEBUG=False`.

**CI: GitHub Actions deploy workflow**

* Set up a deployment workflow (`.github/workflows/deploy.yml`), with caching and conditional run of tests only if relevant files have been changed.

**Minor tweaks** 
* Excluded migrations (with `extend-exclude = ["*/migrations/*"]`) from ruff formatting and then formatted the codebase.
* `.dockerignore` ignores the `.env` file so it does not end up on an image.


## What I deliberately didn't do

* **Didn't actually run `fly deploy`.** The Fly config is written and the prod image is verified locally (built, run, and smoke-tested against a real Postgres), but I don't have a Fly account/org to provision against in this session, so app creation, volume creation, secrets, and the real deploy are left as documented manual steps.
* **Didn't restructure the app layout.** Not moving `blog` (and any future apps) under an `/apps/` directory, and not splitting `User` out into its own `accounts` app.
* **Didn't add any more tests** Didn't set up more tests, coverage tools, etc

## What I'd do next with another day

* **Actually deploy it**: create the Fly org/apps, provision the Postgres volume, set secrets, add `FLY_API_TOKEN` as a repo secret, run the first `fly deploy` on each app (via the new workflow or manually), and confirm the live health check passes.
* **Add DB indexes** — `Post.is_published` + `Post.created_at` are filtered/sorted on every list endpoint; a composite index would help once query counts are already fixed.
* **Reduce the Docker image size** A multi-stage `Dockerfile.fly` to shrink the prod image further.

## AI usage

Done with Claude Code (Sonnet 5).