FROM python:3.10-slim

# Install system dependencies including LibreOffice and fontconfig
RUN apt-get update && apt-get install -y \
    libreoffice \
    fontconfig \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# Copy requirement specifications and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining project files and custom fonts
COPY . .

# Register custom Telugu fonts in system directory
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    cp fonts/* /usr/share/fonts/truetype/custom/ 2>/dev/null || true && \
    fc-cache -f -v

EXPOSE 5000

CMD ["gunicorn", "app:app"]