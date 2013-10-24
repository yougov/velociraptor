#!/bin/bash

mkdir /tmp/lxc
cd /tmp/lxc

# download
wget https://bitbucket.org/yougov/velociraptor/downloads/lxc-0.8.0.tar.gz

tar -zxf lxc-0.8.0.tar.gz

cd lxc-0.8.0
./configure
make
make install
