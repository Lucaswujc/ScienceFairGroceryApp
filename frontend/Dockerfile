# Use the official Node.js runtime as the base image
FROM node:20-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for Expo
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Expo CLI and ngrok globally
RUN npm install @expo/cli @expo/ngrok@^4.1.0

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose the default Expo port
EXPOSE 8081

# Expose additional ports for Metro bundler and development
EXPOSE 19000 19001 19002

# Set environment variables
ENV EXPO_DEVTOOLS_LISTEN_ADDRESS=0.0.0.0
ENV CI=false
ENV FORCE_COLOR=1
ENV NGROK_TIMEOUT=60000

# Use npx expo start as the entry point with tunnel for mobile access
CMD ["npx", "expo", "start" ]
 