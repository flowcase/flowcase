FROM python:3.11-slim

WORKDIR /flowcase

COPY config /flowcase/config
COPY models /flowcase/models
COPY nginx /flowcase/nginx
COPY routes /flowcase/routes
COPY static /flowcase/static
COPY templates /flowcase/templates
COPY utils /flowcase/utils
COPY __init__.py run.py gunicorn.conf.py /flowcase/
COPY requirements.txt /flowcase

# Install system dependencies including Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --trusted-host pypi.python.org -r requirements.txt