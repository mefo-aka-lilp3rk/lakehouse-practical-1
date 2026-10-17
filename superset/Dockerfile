FROM apache/superset:6.0.0

USER root
RUN uv pip install --python /app/.venv/bin/python --no-cache-dir 'apache-superset[trino]==6.0.0'
USER superset
