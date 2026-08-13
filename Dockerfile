FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency resolution and installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the pyproject.toml and lockfile if it exists, for dependency caching
COPY pyproject.toml ./
# Using uv, we can just install directly from pyproject.toml
RUN uv pip install --system -e .

# Alternatively, since we didn't add all deps to pyproject yet, 
# wait we did `uv add` so they are in pyproject.toml
# But wait, uv add modified pyproject.toml on the host. 

COPY . .

# Ensure standard output is unbuffered
ENV PYTHONUNBUFFERED=1

# Expose port for HTTP transport
EXPOSE 8000

# Command to run the streamable-http server by default
CMD ["python", "-m", "src.server", "streamable-http"]
