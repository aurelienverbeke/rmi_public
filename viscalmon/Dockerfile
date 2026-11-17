# Fixed Python version, so we are certain it works
FROM python:3.14.6-trixie as base

SHELL ["/bin/bash", "-c"]

ARG LOGS_GROUP_ID
ARG LOGS_GROUP_NAME

# Install OpenGL for OpenCV and PostgreSQL client
RUN apt update -y && apt install -y curl ca-certificates
RUN install -d /usr/share/postgresql-common/pgdg
RUN curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
COPY pgdg.sources /etc/apt/sources.list.d/pgdg.sources
RUN apt update -y && apt install -y libgl1 postgresql-client-18

RUN pip install uv

# Install python viscalmon library
COPY viscalmon-lib /viscalmon-lib
WORKDIR /viscalmon-lib
RUN uv pip install --system .
ENV PATH="/viscalmon-lib/scripts/:$PATH"
RUN chmod +x /viscalmon-lib/scripts/*

# Add user with specified group so it can write logs outside
# Chmod because de docker daemons remaps the uid/gid at build so 10000->810000
RUN groupadd -g ${LOGS_GROUP_ID} ${LOGS_GROUP_NAME} && \
    useradd -u 10000 -g ${LOGS_GROUP_ID} -m -s /bin/bash runner && \
    chmod 0777 /home/runner

COPY entrypoint.sh /entrypoint.sh
COPY entrypoint.viewer.sh /entrypoint.viewer.sh
RUN chmod +x /entrypoint.sh /entrypoint.viewer.sh

# Create an empty folder for running any code and move into
WORKDIR /app
# Chmod because de docker daemons remaps the uid/gid at build so 10000->810000
RUN chown runner:${LOGS_GROUP_NAME} /app && chmod 0777 /app


USER runner