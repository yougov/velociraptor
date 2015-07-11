#!/bin/bash

exec 2>&1
set -e
set -x

export PATH

apt-get update
apt-get install -y --force-yes \
    autoconf \
    bind9-host \
    bison \
    build-essential \
    coreutils \
    curl \
    daemontools \
    dnsutils \
    ed \
    git \
    graphviz \
    imagemagick \
    iputils-tracepath \
    language-pack-en \
    libbz2-dev \
    libcap-dev \
    libcurl3-dev \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libglib2.0-dev \
    libjpeg-dev \
    libldap2-dev \
    libltdl7 \
    libmagickwand-dev \
    libmysqlclient-dev \
    libncurses5-dev \
    libpcre3-dev \
    libpq-dev \
    libpq5 \
    libreadline6-dev \
    libsasl2-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    libyaml-0-2 \
    libyaml-dev \
    libzmq-dev \
    mercurial \
    netcat-openbsd \
    openssh-client \
    openssh-server \
    python \
    python-dev \
    python3-dev \
    r-base-dev \
    r-mathlib \
    ruby \
    ruby-dev \
    socat \
    syslinux \
    tar \
    telnet \
    zip \
    zlib1g-dev \
    #

# https://github.com/docker/docker/issues/963
apt-get install -y --force-yes --no-install-recommends default-jdk
