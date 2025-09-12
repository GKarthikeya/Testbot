FROM python:3.10-slim

# Install system dependencies and Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 ca-certificates fonts-liberation \
    libnss3 libxss1 libasound2 libatk-bridge2.0-0 libgtk-3-0 \
    libx11-xcb1 libxcb-dri3-0 libxcomposite1 libxdamage1 \
    libxrandr2 xdg-utils \
    libjpeg62-turbo-dev zlib1g-dev \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (latest stable)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV GOOGLE_CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app
COPY ./grok /app/grok

# Expose port (Render uses $PORT automatically)
EXPOSE 10000

# Start the Flask app with Gunicorn
CMD ["gunicorn", "grok.app:app", "--bind", "0.0.0.0:$PORT", "--workers", "1", "--timeout", "120"]
