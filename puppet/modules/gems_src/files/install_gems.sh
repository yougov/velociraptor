#!/bin/bash
wget http://production.cf.rubygems.org/rubygems/rubygems-1.8.24.tgz
tar -xzf rubygems-1.8.24.tgz
cd rubygems-1.8.24
ruby setup.rb
ln -s /usr/bin/gem1.8 /usr/bin/gem
