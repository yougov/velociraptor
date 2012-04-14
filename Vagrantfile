# -*- mode: ruby -*-
# vi: set ft=ruby :
#
# This Vagrantfile and accompanying Puppet manifest are an early stab at
# providing a standard 'yhost' definition for developers to run their own VMs
# that look like production.  Right now it's tuned for velociraptor
# development, which is a bit of a special case.  But I hope that we'll soon
# have a 'yhost' repo with Vagrant and Puppet config so that devs can run their
# own production VM clones.
# -Brent


Vagrant::Config.run do |config|
    # All Vagrant configuration is done here.  For a complete reference of
    # configuration options, , please see the online documentation at
    # vagrantup.com.
    
    # Every Vagrant virtual environment requires a box to build off of.
    config.vm.box = "yhost"

    # The url from where the 'config.vm.box' box will be fetched if it
    # doesn't already exist on the user's system.  If you already have a
    # lucid64 box image sitting around, you can skip this download by doing
    # this before you 'vagrant up':
    # vagrant box add yhost /path/to/lucid64.box
    config.vm.box_url = "http://files.vagrantup.com/lucid64.box"

    # Forward a couple ports for use in development.  So if you visit
    # localhost:8000 in your browser, you'll see whatever's running on that
    # port inside the Vagrant VM.
    config.vm.forward_port 8000, 8000
    config.vm.forward_port 8001, 8001
    config.vm.forward_port 8002, 8002
    config.vm.forward_port 8003, 8003
    config.vm.forward_port 8004, 8004
    config.vm.forward_port 8005, 8005
    config.vm.forward_port 8006, 8006
    config.vm.forward_port 8007, 8007
    config.vm.forward_port 8008, 8008
    config.vm.forward_port 8009, 8009

    # Use Puppet to ensure that certain system packages are installed in the VM
    config.vm.provision :puppet, :module_path => "puppet/modules" do |puppet|
        puppet.manifests_path = "puppet/manifests"
        puppet.manifest_file  = "ydevhost.pp"
    end

    # Make the guest use the host for name resolution, so names on the VPN will
    # work.
    config.vm.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
end
