group { "puppet":
    ensure => "present",
}

class {'vrhost': }
class {'pipdeps': }
class {'pg93': }
class {'current_mongo': }

# Set root password to 'vagrant' so the workers can SSH in and sudo.
user { 'root':
  ensure  => 'present',
  comment => 'root',
  gid     => '0',
  home    => '/root',
  shell   => '/bin/bash',
  uid     => '0',
  password => '$6$JC/PK.2v$itn.8ecXxQIm.vTnxKifHgzUc.4Nh8c/7RXpusn/eUlZ5sIfRPi7sgpPhT5OkDCWQUQ7zBfwwDHP9uqPGwHyq1',
}

Exec { path => '/usr/bin:/bin:/usr/sbin:/sbin' }

# TODO: re-organize these classes around the roles of different hosts in a
# Velociraptor setup: generic, build host, DB/Redis host.

class vrhost {

    Package {ensure => present, require => Exec [firstupdate]}

    package {
        vim:;
        curl:;
        libcurl4-gnutls-dev:;
        libldap2-dev:;
        'libssl0.9.8':; # npm needs these
        libsasl2-dev:;
        libpcre3-dev:;
        libjpeg62-dev:;
        libltdl7:;
        libyaml-dev:;
        lxc:;
        git-core:;
        redis-server:;
        python-setuptools:;
        python-dev:;
        python-pip:;
        python-software-properties:;
    }

    # We have to update first to ensure that apt can find the
    # python-software-properties package that will then let us add PPAs
    exec {
      firstupdate:
        command => "apt-get update",
        timeout => "300";
    }

}

# Use pip to install newer versions of some packages than you can get from apt.
class pipdeps {
    Package {provider => pip, ensure => present,
      require => [Package['python-dev'], Package['python-pip']]}

    package {
      mercurial:;
      virtualenv:;
      virtualenvwrapper:;

      # The host needs to have some VR components available.  Install them from
      # the repo checkout itself.
      '/vagrant/common':;
      '/vagrant/agent':
        require => [Package['/vagrant/common']],
        notify => Service[supervisor];
      '/vagrant/runners':
        require => [Package['/vagrant/common']];
      '/vagrant/builder':
        require => [Package['/vagrant/runners']];
    }

    file { '.bashrc':
        path => '/home/vagrant/.bashrc',
        ensure => file,
        source => 'puppet:///modules/home/bashrc';
    }

    exec {
      custom_supervisor:
        command => "pip install https://bitbucket.org/yougov/velociraptor/downloads/supervisor-3.0b2-dev-vr4.tar.gz",
        require => Package['python-pip'];
    }

    file { 'supervisord.conf':
      path    => '/etc/supervisord.conf',
      ensure  => file,
      source  => 'puppet:///modules/supervisor/supervisord.conf';
    }

    file { 'supervisord.init':
      path    => '/etc/init/supervisor.conf',
      ensure  => file,
      require => Exec[custom_supervisor],
      source  => 'puppet:///modules/supervisor/supervisord.init';
    }

    file { 'supervisor_logdir':
      path    => '/var/log/supervisor',
      ensure  => directory;
    }

    service { "supervisor":
       ensure  => "running",
       enable  => "true",
       require => [
         Exec[custom_supervisor],
         File[supervisor_logdir],
         File['supervisord.init'],
         File['supervisord.conf'],
       ],
    }
}

class pg93 {
    Package {ensure => present, require => Exec [firstupdate]}

    package {
      "postgresql-9.3":;
      "postgresql-server-dev-9.3":;
    }

    file { 'pg_hba.conf':
      path    => '/etc/postgresql/9.3/main/pg_hba.conf',
      ensure  => file,
      require => Package['postgresql-9.3'],
      source  => 'puppet:///modules/postgres/pg_hba.conf',
      notify => Service[postgresql];
    }

    service { "postgresql":
      ensure => "running",
      enable => "true",
      require => Package['postgresql-9.3'];
    }
}

class current_mongo {
  exec {
    mongodb_key:
      command => 'apt-key adv --keyserver hkp://keyserver.ubuntu.com --recv 7F0CEB10';
    mongodb_source:
      command => 'echo "deb http://repo.mongodb.org/apt/ubuntu "$(lsb_release -sc)"/mongodb-org/3.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-3.0.list',
      require => Exec [mongodb_key];
    mongodb_update:
      command => "apt-get update",
      require => Exec [mongodb_source];
  }

  package {
    mongodb-org:
      ensure => present,
      require => Exec [mongodb_update];
  }
}

package { foreman:
    ensure => present,
    provider => gem;
}

# hack around https://bugs.launchpad.net/ubuntu/+source/python2.7/+bug/1115466
file { '/usr/lib/python2.7/_sysconfigdata_nd.py':
   ensure => 'link',
   target => '/usr/lib/python2.7/plat-x86_64-linux-gnu/_sysconfigdata_nd.py',
}

# Provide a nice way to declare PPA dependencies.
define ppa($ppa = "$title", $ensure = present) {

  case $ensure {
    present: {
        $stupid_escapes = '\1-\2'
        $filename = regsubst($ppa, '(^.*)/(.*$)', "$stupid_escapes-$lsbdistcodename.list")

        exec { $ppa:
            command => "add-apt-repository ppa:$ppa;apt-get update",
            require => Package["python-software-properties"],
           	unless => "test -e /etc/apt/sources.list.d/$filename";
        }
    }

    absent:  {
        package {
            ppa-purge: ensure => present;
        }

        exec { $ppa:
            command => "ppa-purge ppa:$ppa;apt-get update",
            require => Package[ppa-purge];
        }
    }

    default: {
      fail "Invalid 'ensure' value '$ensure' for ppa"
    }
  }
}

# Ensure that there's an entry for our hostname in /etc/hosts
file { '/etc/hosts':
    path => '/etc/hosts',
    ensure => file,
    source => 'puppet:///modules/base/hosts';
}
