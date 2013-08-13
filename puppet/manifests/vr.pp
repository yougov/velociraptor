group { "puppet":
    ensure => "present", 
}

class {'vrhost': }
class {'pipdeps': }
class {'pg91': }
class {'currentmongo': }
class {'lxc': }
class {'ruby': }

Exec { path => '/usr/bin:/bin:/usr/sbin:/sbin' }

# TODO: re-organize these classes around the roles of different hosts in a
# Velociraptor setup: generic, build host, DB/Redis host.

# We have to update first to ensure that apt can find the
# python-software-properties package that will then let us add PPAs


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
        git-core:;
        redis-server:;
        python-setuptools:;
        python-dev:;
        python-software-properties:;
    }

    exec {
      firstupdate:
        command => "apt-get update",
        timeout => "300";
    }

}

class ruby {

  package {
      'ruby1.9.3':
        require => Ppa["brightbox/ruby-ng"];
  }  

  exec {
    getbundler:
      command => "gem1.9.3 install bundler",
      require => Package['ruby1.9.3'];
  }

  ppa {
    "brightbox/ruby-ng":;
  }  
}

# Use pip to install newer versions of some packages than you can get from apt.
class pipdeps {
    Package {provider => pip, ensure => present,
      require => [Package['python-dev'], Exec [pip27]]}

    package { 
      mercurial:;
      virtualenv:;
      virtualenvwrapper:;

      # The host needs to have the proc_publisher available.  Install that from
      # the repo checkout itself.
      '/vagrant/common':;
      '/vagrant/agent':
        require => [Service[supervisor], Package['/vagrant/common']],
        notify => Service[supervisor]; 
    }

    file { '.bashrc':
        path => '/home/vagrant/.bashrc',
        ensure => file,
        source => 'puppet:///modules/home/bashrc';
    }

    exec {
      pip27:
        command => "easy_install-2.7 pip",
        require => Package['python-setuptools'];
      custom_supervisor:
        command => "/usr/local/bin/pip-2.7 install https://bitbucket.org/yougov/velociraptor/downloads/supervisor-3.0b2-dev-vr4.tar.gz",
        require => Exec[pip27];  
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

class pg91 {
    package {
      "postgresql-9.1":
        ensure => present,
        ;
      "postgresql-server-dev-9.1":
        ensure => present,
        ;
    }

    file { 'pg_hba.conf':
      path    => '/etc/postgresql/9.1/main/pg_hba.conf',
      ensure  => file,
      require => Package['postgresql-9.1'],
      source  => 'puppet:///modules/postgres/pg_hba.conf';
    }

    exec {
      pgrestart:
        command => "/etc/init.d/postgresql restart",
        require => File['pg_hba.conf'];
    }
}

class currentmongo {
  exec {
    tengenkey:
      command => 'apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10';
    tengensource:
      command => "echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' >> /etc/apt/sources.list",
      unless => 'grep 10gen /etc/apt/sources.list',
      require => Exec [tengenkey];
    tengenupdate:
      command => "apt-get update",
      require => Exec [tengensource];
  }

  package {
    mongodb-10gen:
      ensure => present,
      require => Exec [tengenupdate];
  }
}


class lxc {
  Package {ensure => present, require => Exec [firstupdate]}
  package {
    automake:;
    libcap-dev:;
    libapparmor-dev:;
    build-essential:;
  }

  # put the build script into /tmp
  file { 
  'install_lxc.sh':
    path    => '/tmp/install_lxc.sh',
    ensure  => file,
    require => Package['build-essential', 'automake', 'libcap-dev', 'libapparmor-dev'],
    source  => 'puppet:///modules/lxc/install_lxc.sh';
  '/cgroup':
    ensure => "directory",
    owner  => "root",
    mode   => 755;
  }

  exec {
    build_lxc:
      command => "sh /tmp/install_lxc.sh",
      timeout => "300",
      require => File['install_lxc.sh'];
  }

  mount { "/cgroup":
        device  => 'cgroup',
        fstype  => 'cgroup',
        ensure  => mounted,
        atboot  => true,
        options => 'defaults',
        remounts => false,
        require => File['/cgroup'];
    }
}


package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Package ['ruby1.9.3'];
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

