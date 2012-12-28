# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
    # All Vagrant configuration is done here.  For a complete reference of
    # configuration options, , please see the online documentation at
    # vagrantup.com.
    
    config.vm.box = "precise64"
    config.vm.box_url = "http://files.vagrantup.com/precise64.box"

    # Port for the main dashboard
    config.vm.forward_port 8000, 8000

    # Ports for auto-deployed procs
    config.vm.forward_port 5000, 5000
    config.vm.forward_port 5001, 5001
    config.vm.forward_port 5002, 5002
    config.vm.forward_port 5003, 5003
    config.vm.forward_port 5004, 5004
    config.vm.forward_port 5005, 5005
    config.vm.forward_port 5006, 5006
    config.vm.forward_port 5007, 5007
    config.vm.forward_port 5008, 5008
    config.vm.forward_port 5009, 5009

    # The supervisord web interface
    config.vm.forward_port 9001, 9001

    # Use Puppet to ensure that certain system packages are installed in the VM
    config.vm.provision :puppet, :module_path => "puppet/modules" do |puppet|
        puppet.manifests_path = "puppet/manifests"
        puppet.manifest_file  = "vr.pp"
    end

    # Make the guest use the host for name resolution, so names on the VPN will
    # work.
    config.vm.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
end
