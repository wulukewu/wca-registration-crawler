# Use the official Python image from the Docker Hub
FROM python:3.12

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Google Chrome
RUN apt-get update && \
    apt-get install -y wget && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get -y install google-chrome-stable

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -U selenium

# Accept build arguments for environment variables
ARG EVENT_URL
ARG WCA_ID
ARG BIRTHDAY_YEAR
ARG BIRTHDAY_MONTH
ARG BIRTHDAY_DAY
ARG EMAIL
ARG PHONE

ARG DISCORD_TOKEN
ARG DISCORD_GUILD_ID
ARG DISCORD_CHANNEL_ID

ARG NO_UI

# Run the main.py script
CMD ["python", "main.py"]