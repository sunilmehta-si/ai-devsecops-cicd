# Minimal, non-root image for the sample gateway. The app uses only the standard library.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /srv
COPY apps/ ./apps/

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8080'))"]
CMD ["python", "-m", "apps.llm_gateway.server"]
