# Dockerfile for Flask backend
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application source code into the /app directory inside the container.
COPY src .

# Run the multiCloud application using gunicorn, a production-ready WSGI (Web Server Gateway Interface) server for Python web applications like Flask
# main_appy refers to the Python module under src/main_app.py 
# bind all available network interfaces (0.0.0.0) on port 5000. The application can be accessible from outside the container.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main_app:multiCloud"]