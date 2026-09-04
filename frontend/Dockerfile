# StockAI frontend — build with CRA/craco, serve static with nginx
FROM node:20-slim AS build
WORKDIR /app/frontend

# REACT_APP_BACKEND_URL is baked at BUILD time (CRA env). Pass via --build-arg.
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM nginx:1.27-alpine
COPY --from=build /app/frontend/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
