# Stage 1: Build the React app
FROM node:16 as build

# Set the working directory
WORKDIR /app

# Copy package.json
COPY package.json  ./

# Install dependencies
RUN npm install

# Copy the application source code into the /app directory inside the container.
COPY src .

# Build the React app
# compile index.js and other components into static files 
RUN npm run build
# Outcome:
#build/
#    ├── index.html
#    ├── static/
#    │   ├── js/
#    │   │   └── main.[hash].js
#    │   ├── css/
#    │   │   └── main.[hash].css
#    └── assets/
#


# Stage 2: Serve the React app using Nginx
FROM nginx:alpine

# Copy the built React app from the previous stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy the Nginx configuration file
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Based on the conf, nginx serves index.html file when requesting '/'
# Expose port 80
EXPOSE 80

# Start Nginx and ensure that Nginx runs in the foreground, which is necessary for Docker containers to stay running.
CMD ["nginx", "-g", "daemon off;"]