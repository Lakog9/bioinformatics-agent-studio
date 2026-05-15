FROM bioconductor/bioconductor_docker:RELEASE_3_20

# ============================================
# System dependencies (Python pip + Quarto installer)
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        curl \
        gdebi-core \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# ============================================
# Quarto (HTML report renderer)
# ============================================
RUN curl -L -o /tmp/quarto.deb \
        https://github.com/quarto-dev/quarto-cli/releases/download/v1.5.57/quarto-1.5.57-linux-amd64.deb \
 && gdebi -n /tmp/quarto.deb \
 && rm /tmp/quarto.deb \
 && quarto --version

# ============================================
# R packages (DESeq2 + annotation + enrichment + plotting)
# Bioconductor image has BiocManager pre-installed.
# ============================================
RUN R -e 'BiocManager::install(c("DESeq2", "org.Hs.eg.db"), update=FALSE, ask=FALSE)' \
 && R -e 'install.packages(c("gprofiler2", "jsonlite", "pheatmap", "ggplot2"), repos="https://cloud.r-project.org")' \
 && R -e 'stopifnot(require(DESeq2), require(org.Hs.eg.db), require(gprofiler2))'

# ============================================
# Python packages (agents + ML)
# ============================================
RUN pip3 install --break-system-packages --no-cache-dir \
        anthropic \
        pandas \
        scikit-learn \
        matplotlib \
        seaborn \
        requests \
        python-dotenv

# ============================================
# Application code
# ============================================
WORKDIR /app
COPY agents/   /app/agents/
COPY projects/ /app/projects/
COPY bioagent.py /app/

# ============================================
# Default entrypoint runs the CLI.
# Users mount data and output volumes:
#   docker run --rm \
#     -v /local/data:/data \
#     -v /local/output:/output \
#     --env-file .env \
#     bioagent-studio \
#     --counts /data/counts.csv ...
# ============================================
ENTRYPOINT ["python3", "/app/bioagent.py"]
CMD ["--help"]
