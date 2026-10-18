FROM node:22-bookworm-slim AS frontend
ARG AURELIO_COMMIT=2be2ddb2b95dad0947314c818f952c3412e8e861
ARG AURELIO_SHA256=a1df2814e9864baf6d54d3859ae46ab435e39c09ba5ab689a3d46f92ac890d6d
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/aurelio
RUN curl -fL --retry 3 "https://codeload.github.com/LosaLosSantos/aurelio-finance/tar.gz/${AURELIO_COMMIT}" -o /tmp/source.tar.gz \
 && echo "${AURELIO_SHA256}  /tmp/source.tar.gz" | sha256sum -c - \
 && tar xzf /tmp/source.tar.gz --strip-components=1 -C /opt/aurelio && rm /tmp/source.tar.gz
WORKDIR /opt/aurelio/frontend
RUN npm ci && npm run build

FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git curl && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv==0.9.4 fastapi==0.136.3 uvicorn==0.48.0 httpx==0.28.1 \
 && useradd --uid 1000 --create-home app
COPY --from=frontend /opt/aurelio/backend /opt/aurelio/backend
COPY --from=frontend /opt/aurelio/frontend/dist /opt/aurelio/frontend/dist
WORKDIR /opt/aurelio/backend
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --python /usr/local/bin/python
COPY railway /opt/railway
ENV UV_PYTHON_DOWNLOADS=never
ENV APP_KIND=aurelio UPSTREAM_VERSION=2be2ddb2b95d PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/opt/railway/launcher.py"]
