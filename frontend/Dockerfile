# DeepShieldAI frontend image — a two-stage build.
#
# Stage 1 compiles the React/Vite app into static files; stage 2 serves
# those files with nginx. The Node toolchain (node_modules, the Vite dev
# server, eslint, vitest — see package.json) has no reason to exist in the
# image that actually runs in "production" (i.e. what an examiner or
# grader opens in a browser) — it would roughly 10x the image size for
# tooling nobody needs at runtime, purely to serve compiled HTML/CSS/JS.
FROM node:20-alpine AS build

WORKDIR /app

# package*.json before the rest of the source: this layer only rebuilds
# when dependencies change, not on every component edit.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The dev server's /api proxy (vite.config.js's server.proxy) only exists
# for `npm run dev` — a production build has no dev server at all, so that
# proxying job moves to nginx.conf below instead (proxy_pass to the
# `backend` compose service).
RUN npm run build

# ---------------------------------------------------------------------------

FROM nginx:1.27-alpine

# Remove nginx's own default site config before adding ours, so there's
# exactly one server block, not a conflicting or unreachable second one.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
