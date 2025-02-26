FROM alpine:3.21 AS tools
RUN apk add --no-cache \
    bash \
    git \
    build-base \
    go \
    curl
RUN git clone https://github.com/Kalon-Kelley/helm-dynamic-dependencies.git /hd
RUN git clone https://github.com/helm/helm.git /h
RUN cd /hd && make
RUN cd /h && make
RUN mv /hd/bin/helm /hd/bin/helm-dyn

FROM rancher/k3s AS k3s

ENV PATH="/h/bin:/hd/bin:/usr/bin:/usr/local/bin:$PATH"
COPY --from=tools /hd /hd
COPY --from=tools /h /h
ENV KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
RUN mkdir -p /charts
WORKDIR /charts
