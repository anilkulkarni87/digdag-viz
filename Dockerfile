FROM python:3.11-slim

LABEL maintainer="Treasure Data"
LABEL description="Digdag workflow visualization tool"
LABEL version="2.0.0"

# Install Graphviz system dependency
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        graphviz \
        graphviz-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install the package
RUN pip install --no-cache-dir .

# Create output directory
RUN mkdir -p /output

# Set entrypoint to the installed console script
ENTRYPOINT ["digdag-viz"]
CMD ["--help"]
