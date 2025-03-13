FROM python:3.11-alpine

RUN apk add --no-cache \
    bash \
    git \
    curl \
    make \
    go \
    docker \
    openrc \
    && curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash \
    && ln -s /usr/local/bin/k3d /usr/bin/k3d

RUN git clone https://github.com/Kalon-Kelley/helm-dynamic-dependencies.git /hd
RUN git clone https://github.com/helm/helm.git /h
RUN cd /hd && make
RUN cd /h && make
RUN mv /hd/bin/helm /hd/bin/helm-dyn

ENV PATH="/h/bin:/hd/bin:/usr/local/bin:$PATH"

RUN mkdir -p /charts
WORKDIR /charts
RUN export HELM_EXPERIMENTAL_OCI=1

COPY requirements.txt ./requirements.txt
RUN python3 -m venv /venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

COPY evaluation.py ./evaluation.py

ENTRYPOINT ["sh", "-c", "dockerd --host=unix:///var/run/docker.sock & k3d cluster delete mycluster & k3d cluster create mycluster & tail -f /dev/null"]
