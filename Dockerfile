FROM python:3.10-slim

# Enable contrib repo for font packages
RUN echo "deb http://deb.debian.org/debian bookworm main contrib" > /etc/apt/sources.list.d/contrib.list

# Install LibreOffice and essential fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fontconfig \
    fonts-noto \
    fonts-noto-color-emoji \
    fonts-opensymbol \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Register custom fonts
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    cp fonts/* /usr/share/fonts/truetype/custom/ 2>/dev/null || true && \
    fc-cache -f

# Start Gunicorn dynamically reading Render's PORT environment variable
CMD sh -c "gunicorn --timeout 300 -w 2 -b 0.0.0.0:${PORT:-10000} app:app"