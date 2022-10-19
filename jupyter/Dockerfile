# pull official base image
FROM jupyterhub/jupyterhub:3

RUN apt-get update && apt-get install -y wget \
    python3-pip \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker repo
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
RUN apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

COPY *.py /srv/jupyterhub/
COPY start.sh /srv/jupyterhub

RUN pip install --upgrade pip
RUN pip install dockerspawner

ENTRYPOINT sh start.sh
