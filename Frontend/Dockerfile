# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built files and server
COPY --from=build /app/build ./build
COPY --from=build /app/serve-build.js ./

# Install only production dependencies for the server
RUN npm install --only=production

EXPOSE 3000

CMD ["node", "serve-build.js"]
