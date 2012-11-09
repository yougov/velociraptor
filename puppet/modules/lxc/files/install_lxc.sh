#!/bin/bash

mkdir /tmp/lxc
cd /tmp/lxc

# download
wget http://lxc.sourceforge.net/download/lxc/lxc-0.8.0-rc2.tar.gz

tar -zxf lxc-0.8.0-rc2.tar.gz

cd lxc-0.8.0-rc2
./configure
make
make install
