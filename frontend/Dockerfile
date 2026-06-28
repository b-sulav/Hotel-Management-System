FROM nginx:alpine

# Install curl for healthchecks
RUN apk add --no-cache curl \
    && rm -rf /etc/nginx/conf.d/default.conf

# Copy only frontend assets into document root
COPY frontend/. /usr/share/nginx/html/

# Install the actual nginx config (dashboard proxy, SSL, headers)
COPY nginx/conf.d/ /etc/nginx/conf.d/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
