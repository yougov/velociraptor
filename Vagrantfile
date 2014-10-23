# -*- mode: ruby -*-
# vi: set ft=ruby :
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    # All Vagrant configuration is done here.  For a complete reference of
    # configuration options, , please see the online documentation at
    # vagrantup.com.

    config.vm.box = "trusty64"
    config.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"

    # Port for the main dashboard
    config.vm.network "forwarded_port", guest: 8000, host: 8000


    # Port for the khartoum fileserver
    config.vm.network "forwarded_port", guest: 8001, host: 8001

    # Ports for auto-deployed procs
    config.vm.network "forwarded_port", guest: 5000, host: 5000
    config.vm.network "forwarded_port", guest: 5001, host: 5001
    config.vm.network "forwarded_port", guest: 5002, host: 5002
    config.vm.network "forwarded_port", guest: 5003, host: 5003
    config.vm.network "forwarded_port", guest: 5004, host: 5004
    config.vm.network "forwarded_port", guest: 5005, host: 5005
    config.vm.network "forwarded_port", guest: 5006, host: 5006
    config.vm.network "forwarded_port", guest: 5007, host: 5007
    config.vm.network "forwarded_port", guest: 5008, host: 5008
    config.vm.network "forwarded_port", guest: 5009, host: 5009
    config.vm.network "forwarded_port", guest: 5010, host: 5010
    config.vm.network "forwarded_port", guest: 5011, host: 5011
    config.vm.network "forwarded_port", guest: 5012, host: 5012
    config.vm.network "forwarded_port", guest: 5013, host: 5013
    config.vm.network "forwarded_port", guest: 5014, host: 5014

    # The supervisord web interface
    config.vm.network "forwarded_port", guest: 9001, host: 9001

    # Use Puppet to ensure that certain system packages are installed in the VM
    config.vm.provision :puppet, :module_path => "puppet/modules" do |puppet|
        puppet.manifests_path = "puppet/manifests"
        puppet.manifest_file  = "vr.pp"
        puppet.facter = {
            "fqdn" => "trusty64"
        }
    end

    # Make the guest use the host for name resolution, so names on the VPN will
    # work.
    config.vm.provider :virtualbox do |vb|
        vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    end
end
