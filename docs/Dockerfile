# Single stage on purpose: `next start` needs node_modules at runtime, so a
# builder/runner split would have to reinstall or copy them back anyway.
#
# The build context is this `docs/` directory (see .dockerignore). The generated
# reference pages under content/docs/reference/ are committed, so the container
# never needs the Python integration source — the drift guard in CI is what keeps
# them honest.
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npx fumadocs-mdx
RUN npm run build

# Railway injects $PORT; these defaults keep a plain `docker run -p 8080:8080` working.
ENV PORT=8080
ENV HOSTNAME=0.0.0.0
EXPOSE 8080

CMD ["npm", "run", "start"]
