# Use an official lightweight Python image
FROM python:3.10-slim

# Install LibreOffice, font utilities, and core font packages
RUN apt-get update && apt-get install -y \
    libreoffice \
    fontconfig \
    fonts-dejavu \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy dependency requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Copy all custom Telugu and Anu Script fonts into system font directory and update cache
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    cp fonts/* /usr/share/fonts/truetype/custom/ 2>/dev/null || true && \
    fc-cache -f -v

# Expose port 10000 for Render
EXPOSE 10000

# Start Gunicorn server with 300-second timeout for large document processing
CMD ["gunicorn", "--timeout", "300", "-w", "2", "-b", "0.0.0.0:10000", "app:app"]