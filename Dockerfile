# exams-generator with every built-in toolchain: GHC, GCC/G++, Python + mypy,
# and pandoc + LaTeX for PDFs.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv \
        ghc \
        gcc g++ libc6-dev \
        pandoc \
        texlive-latex-base texlive-latex-recommended texlive-fonts-recommended lmodern \
        texlive-lang-spanish \
        ghostscript \
        git openssh-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python3 -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install ".[typecheck]"

RUN useradd --create-home --uid 1000 exams \
    && mkdir -p /data /exams \
    && chown exams:exams /data /exams
USER exams

ENV PATH="/venv/bin:${PATH}" \
    EXAMS_TRANSPORT=http \
    EXAMS_HTTP_HOST=0.0.0.0 \
    EXAMS_HTTP_PORT=8765 \
    EXAMS_DATA_DIR=/data \
    EXAMS_DIR=/exams

EXPOSE 8765
VOLUME ["/exams"]
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz')"
ENTRYPOINT ["exams-generator"]
