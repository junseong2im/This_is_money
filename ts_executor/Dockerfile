# TypeScript Executor Server
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build 2>/dev/null || npx tsc

# Environment variables
ENV PORT=3001

EXPOSE 3001

CMD ["node", "dist/server.js"]
