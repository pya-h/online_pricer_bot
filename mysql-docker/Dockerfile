# Use the official MySQL image from the Docker Hub
FROM mysql:latest

# Set environment variables for MySQL configuration
ENV MYSQL_ROOT_PASSWORD=""
ENV MYSQL_DATABASE="online_pricer"
ENV MYSQL_ALLOW_EMPTY_PASSWORD=true
# Expose the MySQL port
EXPOSE 3306

# Add a health check to ensure the database is up and running
HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 CMD mysqladmin ping -h localhost || exit 1
