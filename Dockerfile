# Use the official Python image from the Docker Hub, slim version for smaller size
FROM python:3.12.3-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements.txt file into the container at /app
COPY requirements.txt .

# Install the Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose port 8501 to allow access to the Streamlit app
# EXPOSE 8501 (save it for compose.yaml)

# Command to run the Streamlit app
CMD ["streamlit", "run", "chatbot.py"]


