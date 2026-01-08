# Lightweight Nginx server to serve static HTML
FROM nginx:alpine

# Copy the static HTML file to Nginx's default public directory
# Rename website.html to index.html so it serves automatically
COPY website.html /usr/share/nginx/html/index.html

# Expose port 80
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
