FROM ubuntu:22.04

RUN apt update && apt install -y software-properties-common
RUN add-apt-repository ppa:longsleep/golang-backports
RUN apt update && apt install -y \
    git \
    build-essential \
    golang-go \
    curl
RUN git clone https://github.com/Kalon-Kelley/helm-dynamic-dependencies.git \
    /helm-src
WORKDIR /helm-src

RUN make
ENV PATH="/helm-src/bin:$PATH"

RUN mkdir -p /charts
RUN mkdir -p /log

COPY entrypoint.sh /run/
RUN curl -sfL https://get.k3s.io | INSTALL_K3S_SKIP_ENABLE=true sh -
ENV KUBECONFIG="/etc/rancher/k3s/k3s.yaml"

WORKDIR /charts
ENTRYPOINT ["/run/entrypoint.sh"]
