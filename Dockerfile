# Minimal, non-root image for the sample gateway. The app uses only the standard library.
# Pinned by digest, so a build is the same image until the pin is bumped (Dependabot follows the digest).
FROM python:3.15.1-slim@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Debian's security fixes reach the official image only when it is next rebuilt, which can be days after the
# advisory (zlib, DSA-6613-1, was fixed in trixie-security before the image was rebuilt). Take them at build
# time so the image scan judges what actually ships.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# The gateway uses only the standard library, so the image ships without pip. pip carries its own copies of
# urllib3, msgpack and pkg_resources, which the image scan judges like any other code in the image.
RUN python -m pip uninstall --yes --no-input pip \
    && rm -f /usr/local/lib/python3*/ensurepip/_bundled/*.whl

RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /srv
COPY apps/ ./apps/

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8080'))"]
CMD ["python", "-m", "apps.llm_gateway.server"]
