FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# API_URL is server-only (used by Next's rewrites, resolved inside the Docker
# network). NEXT_PUBLIC_API_URL is inlined into the client bundle at build time —
# it must be reachable from the *browser*, not just from inside Docker, so it
# defaults to the published host port rather than the internal service name.
ARG API_URL=http://api:8000
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV API_URL=$API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ARG API_URL=http://api:8000
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV API_URL=$API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=builder --chown=node:node /app/package*.json ./
COPY --from=builder --chown=node:node /app/.next ./.next
COPY --from=builder --chown=node:node /app/next.config.js ./

RUN npm ci --omit=dev

USER node
EXPOSE 3000
CMD ["npm", "run", "start"]

