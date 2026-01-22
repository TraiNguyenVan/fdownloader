FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install firefox
# We use Firefox as it is often less detectable or handles some things differently, 
# but Chromium is also fine. Installing both to be safe or just one to save space.
# The base image already has browsers installed usually, but `playwright install` ensures it matches.

COPY . .

# ENTRYPOINT ["python", "main.py"]
# Commented out to allow flexible commands from docker-compose

