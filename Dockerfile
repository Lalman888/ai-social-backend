# Stage 1: Build environment with dependencies
FROM python:3.10-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2, Pillow)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# Stage 2: Production environment
FROM python:3.10-slim

# Create a non-root user and group
RUN addgroup --system app && adduser --system --ingroup app app

# Set work directory
WORKDIR /home/app/web

# Copy installed dependencies from builder stage
COPY --from=builder /wheels /wheels
# Install dependencies from wheels
RUN pip install --no-cache /wheels/*

# Copy application code
# Ensure .dockerignore is present to exclude unnecessary files
COPY . .

# Change ownership to the app user
RUN chown -R app:app /home/app/web

# Switch to the non-root user
USER app

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use the host 0.0.0.0 to accept connections from outside the container
# The entrypoint/cmd can be overridden in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
