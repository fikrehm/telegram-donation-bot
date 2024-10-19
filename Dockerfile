# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements and other files
COPY pyproject.toml ./
COPY main.py ./
COPY .env ./

# Install Poetry
RUN pip install poetry

# Install dependencies
RUN poetry install --no-dev

# Command to run the bot
CMD ["poetry", "run", "python", "main.py"]
