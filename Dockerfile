# Use an official Python runtime as base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (better layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot code
COPY . .

# Command to run the bot
CMD ["python", "bot.py"]
