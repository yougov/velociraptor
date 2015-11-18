#!/bin/bash

# If you provide any command line argument to this script it will run in "dev
# mode", which means:
# 1. Some prod-specific cleanup is skipped, like removing the setuid bit from
#    all binaries.
# 2. Some dev-specific packages will be installed, like Supervisor, Postgres,
#    etc.
export DEV_ENV=$1

echo -e "BEGINNING PRODUCTION-SPECIFIC PROVISIONING"

exec 2>&1
set -e
set -x

export PATH

cat > /etc/apt/sources.list <<EOF
deb http://archive.ubuntu.com/ubuntu trusty main
deb http://archive.ubuntu.com/ubuntu trusty-security main
deb http://archive.ubuntu.com/ubuntu trusty-updates main
deb http://archive.ubuntu.com/ubuntu trusty universe
EOF

###################
# PROD: APT DEPS
###################

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
    libevent-1.4-2 \
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

# language packs are usually installed on cedarish, but Ubuntu's been lazy
# about updating their dependencies, leading to things like https://paste.yougov.net/0Tf1g
# comment them out for now.
#apt-cache search language-pack \
    #| cut -d ' ' -f 1 \
    #| grep -v '^language\-pack\-\(gnome\|kde\)\-' \
    #| grep -v '\-base$' \
    #| xargs apt-get install -y --force-yes --no-install-recommends

###################
# PROD: CLEANUP
###################
if [ -z "$DEV_ENV" ]; then
    echo -e "\nDEV_ENV not set. Doing production cleanup"
    cd /
    rm -rf /var/cache/apt/archives/*.deb
    rm -rf /root/*
    rm -rf /tmp/*

    # remove SUID and SGID flags from all binaries
    function pruned_find() {
      find / -type d \( -name dev -o -name proc \) -prune -o $@ -print
    }

    # Once you do this, sudo is disabled.
    pruned_find -perm /u+s | xargs -r chmod u-s
    pruned_find -perm /g+s | xargs -r chmod g-s

    # remove non-root ownership of files
    chown root:root /var/lib/libuuid

    set +x
    echo -e "\nRemaining suspicious security bits:"
    (
      pruned_find ! -user root
      pruned_find -perm /u+s
      pruned_find -perm /g+s
      pruned_find -perm /+t
    ) | sed -u "s/^/  /"
else
    echo -e "\nDEV_ENV set. Skipping production cleanup"
fi

echo -e "\nInstalled versions:"
(
  git --version
  ruby -v
  gem -v
  python -V
  hg version -q
) | sed -u "s/^/  /"


###################
# PROD: YG CERT
###################

echo -e "\nInstalling yougov.local public cert"
cat > /etc/ssl/YOUGOV-AD01-CA.rencer <<EOF
-----BEGIN CERTIFICATE-----
MIIDgzCCAmugAwIBAgIQOl4MX1lZj7dMpCvpHrz0rzANBgkqhkiG9w0BAQUFADBI
MRUwEwYKCZImiZPyLGQBGRYFbG9jYWwxFjAUBgoJkiaJk/IsZAEZFgZZT1VHT1Yx
FzAVBgNVBAMTDllPVUdPVi1BRDAxLUNBMB4XDTExMDgxODEwMDkwMloXDTIxMDgx
ODEwMTkwMVowSDEVMBMGCgmSJomT8ixkARkWBWxvY2FsMRYwFAYKCZImiZPyLGQB
GRYGWU9VR09WMRcwFQYDVQQDEw5ZT1VHT1YtQUQwMS1DQTCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBAL48Z98AjlKDf43EmQJfQ2J+0on8KhZUnEQ3Lru0
FncadLt02AKhoKCFbqewZgO9xlouJiIa2SfNTL1CJ3N00z1cKprcVyvutGxFsMr0
qPVJS9TaXpqSztDkN+gC7mn6iv/ZD0hGO9jMvn5oaG4JTlfiJwNO31nApAXZqdIv
fcexMPQ65eUipFj7MHhK1VgtQc73pZOr1SP+AR0D1+JdLunrbmRhmqUOpoX6F/55
ZBHPnAMxd7BlOE3P9WzlVd14tQRS4oBi0+TUp456j60IU7+khw/P5rUAwZj0P0fU
whR/F6rjni7sPPqV5drtlbDkMML2H/r8Ar1BKchi96oJDRECAwEAAaNpMGcwEwYJ
KwYBBAGCNxQCBAYeBABDAEEwDgYDVR0PAQH/BAQDAgGGMA8GA1UdEwEB/wQFMAMB
Af8wHQYDVR0OBBYEFFnkLMjIXixWvo62uL8duJ5m+RrZMBAGCSsGAQQBgjcVAQQD
AgEAMA0GCSqGSIb3DQEBBQUAA4IBAQBm1CNqy3j+7aHBAKhzZG8LCncAGtGJknZe
a1uPPh4+PZ+xa28UjF/eL0LLXswe+6ZLnV3DYBUtl8ArbGF9fayTi9oBMKSyfFFe
VbfkVRxX/exXray561n6WXCXVvEX6XAtPvBcWyI1oIpDpdy0+zAfDwLYTdUEEiI9
w4nxTZKBAoOdCsB2KSoMdsdQX/Ccl8gFUDf0PMFCEXNAx3VUw++2GUpW/OX+A8Qx
afe3i8yHqpAMv0Ut7mlhfNVk85EPKtXEqD3rgPoB9T/5/cfsuuNXCOJp3Y03vqvc
OhKSEkbDRJE+ze5YzNFIEDi/csbiWgi7cFMXYHyr+kO4/dTkkznR
-----END CERTIFICATE-----
EOF

echo -e "\nFINISHED PRODUCTION-SPECIFIC PROVISIONING"

if [ $DEV_ENV ] ; then
echo -e "\nBEGINNING DEV-SPECIFIC PROVISIONING"

#######################
# DEV: BASIC/MISC STUFF
#######################

# Set root passwd in VM so VR workers can SSH in.
echo  "root:vagrant" | chpasswd

cat > /etc/hosts <<EOF
127.0.0.1 localhost vagrant-ubuntu-trusty-64

# The following lines are desirable for IPv6 capable hosts
::1 ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts
EOF

#######################
# DEV: PACKAGES
#######################

# Keep this package list alphabetized
apt-get install -y --force-yes \
    htop \
    lxc \
    python-pip \
    python-setuptools \
    python-software-properties \
    redis-server \
    rabbitmq-server \
    vim \
    #

# Keep this package list alphabetized.  Packages should be installable from
# cheese.yougov.net.
pip install -i http://cheese.yougov.net \
    virtualenv \
    virtualenvwrapper \
    vr.agent \
    vr.runners \
    vr.builder \
    https://bitbucket.org/yougov/velociraptor/downloads/supervisor-3.0b2-dev-vr4.tar.gz \
    #

gem install foreman

#######################
# DEV: ~/.bashrc
#######################

cat > /home/vagrant/.bashrc <<EOF
case \$- in
    *i*) ;;
      *) return;;
esac

HISTCONTROL=ignoreboth

shopt -s histappend

HISTSIZE=1000
HISTFILESIZE=2000

shopt -s checkwinsize

[ -x /usr/bin/lesspipe ] && eval "\$(SHELL=/bin/sh lesspipe)"

if [ -z "\${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=\$(cat /etc/debian_chroot)
fi

case "\$TERM" in
    xterm-color) color_prompt=yes;;
esac

#force_color_prompt=yes

if [ -n "\$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    color_prompt=yes
    else
    color_prompt=
    fi
fi

if [ "\$color_prompt" = yes ]; then
    PS1='\${debian_chroot:+(\$debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\\$ '
else
    PS1='\${debian_chroot:+(\$debian_chroot)}\u@\h:\w\\$ '
fi
unset color_prompt force_color_prompt

case "\$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;\${debian_chroot:+(\$debian_chroot)}\u@\h: \w\a\]\$PS1"
    ;;
*)
    ;;
esac

if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "\$(dircolors -b ~/.dircolors)" || eval "\$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias alert='notify-send --urgency=low -i "\$([ \$? = 0 ] && echo terminal || echo error)" "\$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert\$//'\'')"'

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python2.7
source /usr/local/bin/virtualenvwrapper.sh
EOF
# end /home/vagrant/.bashrc

#######################
# DEV: SUPERVISOR
#######################

cat > /etc/supervisord.conf <<EOF
[unix_http_server]
file=/var/run//supervisor.sock
chmod=0700

[supervisord]
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[inet_http_server]
port = *:9001
username = vagrant
password = vagrant

[supervisorctl]
serverurl=unix:///var/run//supervisor.sock

[include]
files = /etc/supervisor/conf.d/*.conf /apps/procs/*/proc.conf

[eventlistener:proc_publisher]
command=proc_publisher
events=PROCESS_STATE,PROCESS_GROUP,TICK_60
environment=REDIS_URL="redis://localhost:6379/0",HOSTNAME=vagrant-ubuntu-trusty-64
stderr_logfile=/var/log/proc_publisher.log

[rpcinterface:vr]
supervisor.rpcinterface_factory = vr.agent.rpc:make_interface
EOF

cat > /etc/init/supervisord.conf <<EOF
description "supervisor"

start on runlevel [2345]
stop on runlevel [06]

limit nofile 65536 65536

respawn

exec supervisord --nodaemon
EOF

mkdir -p /var/log/supervisor
service supervisord restart

###################
# DEV: RABBIT CONFIG
###################
cat > /etc/rabbitmq/enabled_plugins << EOF
[rabbitmq_management].
EOF
/etc/init.d/rabbitmq-server restart

###################
# DEV: POSTGRES
###################
cat > /etc/apt/sources.list.d/pgdg.list <<EOF
deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main
EOF

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  apt-key add -
apt-get update

apt-get install -y --force-yes \
    postgresql-9.4 \
    postgresql-server-dev-9.4 \
    postgresql-contrib-9.4 \
    #

cat > /etc/postgresql/9.4/main/pg_hba.conf <<EOF
local   all             postgres                                trust
local   all             all                                     trust
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
local   replication     postgres                                trust
EOF


cat > /etc/postgresql/9.4/main/postgresql.conf <<EOF
data_directory = '/var/lib/postgresql/9.4/main'
hba_file = '/etc/postgresql/9.4/main/pg_hba.conf'
ident_file = '/etc/postgresql/9.4/main/pg_ident.conf'
external_pid_file = '/var/run/postgresql/9.4-main.pid'
port = 5432
max_connections = 100
unix_socket_directories = '/var/run/postgresql'
ssl = true
ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key'
shared_buffers = 128MB
# dynamic_shared_memory_type = posix
log_line_prefix = '%t [%p-%l] %q%u@%d '
log_timezone = 'UTC'
stats_temp_directory = '/var/run/postgresql/9.4-main.pg_stat_tmp'
datestyle = 'iso, mdy'
timezone = 'UTC'
lc_messages = 'en_US.UTF-8'
lc_monetary = 'en_US.UTF-8'
lc_numeric = 'en_US.UTF-8'
lc_time = 'en_US.UTF-8'
default_text_search_config = 'pg_catalog.english'
EOF

service postgresql restart
set +e
createuser -U postgres --superuser vagrant
createdb -U postgres --owner=vagrant vagrant
set -e

###################
# DEV: MONGO
###################
apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' >> /etc/apt/sources.list
apt-get update
apt-get install -y --force-yes mongodb-10gen

####################
# DEV: ELASTICSEARCH
####################

wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo 'deb http://packages.elastic.co/elasticsearch/1.5/debian stable main' >> /etc/apt/sources.list
apt-get update
apt-get install -y --force-yes elasticsearch
update-rc.d elasticsearch defaults 95 10
/etc/init.d/elasticsearch start

###################
# DEV: CLEANUP
###################
# Vagrant has Puppet and Chef in all boxes by default.  Clean them out.
apt-get remove -y --force-yes \
    chef \
    puppet \
    #
apt-get autoremove -y --force-yes

echo -e "\nFINISHED DEV-SPECIFIC PROVISIONING"
fi
exit 0


