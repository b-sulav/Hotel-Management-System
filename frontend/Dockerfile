FROM nginx:alpine

# Install curl for healthchecks
RUN apk add --no-cache curl \
    && rm -rf /etc/nginx/conf.d/default.conf

COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
