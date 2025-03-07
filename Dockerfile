from ghcr.io/astral-sh/uv:python3.10-bookworm-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --frozen

CMD [ "uv", "run", "main.py" ]