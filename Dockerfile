# Base image
FROM python:3.12-alpine

# Set the working directory
WORKDIR /app

# Copy files to the working directory
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# For production, install Gunicorn
RUN pip install gunicorn

# Expose the Flask application port
EXPOSE 5000

# Run the Flask application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
