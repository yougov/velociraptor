group { "puppet":
    ensure => "present", 
}

Exec { path => '/usr/bin:/bin:/usr/sbin:/sbin' }

# TODO: re-organize these classes around the roles of different hosts in a
# Velociraptor setup: generic, build host, DB/Redis host.

# We have to update first to ensure that apt can find the
# python-software-properties package that will then let us add PPAs

class yhost {
    
    Package {ensure => present, require => Exec [firstupdate]}

    package {
        ruby:;
        libevent-dev:;
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
    }

    exec {
      firstupdate:
        command => "apt-get update",
        timeout => "300";
      supervisor_logdir:
        command => "mkdir -p /var/log/supervisor";

      custom_supervisor:
        command => "/usr/local/bin/pip-2.7 install -i http://cheese.yougov.net supervisor==3.0b3events",
        require => Exec[pip27];

      start_supervisor:
        command => "start supervisor",
        require => [File["supervisord.conf"], File["supervisord.init"],
                                              Exec[supervisor_logdir]],
        # Don't try starting if we're already started.
        unless => 'ps aux | grep supervisor | grep -v "grep"' ;
    }

    # ensure that supervisord's config has the line to include
    # /apps/procs/*/proc.conf
    file { 'supervisord.conf':
      path    => '/etc/supervisord.conf',
      ensure  => file,
      require => Exec[custom_supervisor],
      source  => 'puppet:///modules/supervisor/supervisord.conf';
    }

    file { 'supervisord.init':
      path    => '/etc/init/supervisor.conf',
      ensure  => file,
      require => Exec[custom_supervisor],
      source  => 'puppet:///modules/supervisor/supervisord.init';
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
      '/vagrant/libraptor':
        require => Exec[custom_supervisor];
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

# 
class lxc {
  Package {ensure => present, require => Exec [firstupdate]}
  package {
    automake:;
    libcap-dev:;
    libapparmor-dev:;
    build-essential:;
  }

  # put the build script into /tmp
  file { 'install_lxc.sh':
    path    => '/tmp/install_lxc.sh',
    ensure  => file,
    require => Package['build-essential', 'automake', 'libcap-dev', 'libapparmor-dev'],
    source  => 'puppet:///modules/lxc/install_lxc.sh';
  }

  exec {
    build_lxc:
      command => "sh /tmp/install_lxc.sh",
      timeout => "300",
      require => File['install_lxc.sh'];
    mount_cgroup:
      command => "mkdir -p /cgroup; mount none -t cgroup /cgroup",
      require => Exec['build_lxc'],
      unless => 'mount | grep "/cgroup type cgroup"';
  }
}

package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Package [ruby];
}

# Include the self-signed SSL cert that yg.ldap needs to make secure
# connections to our domain controllers.
file { 'ldap_cert':
  path    => '/etc/ssl/YOUGOV-AD01-CA.rencer',
  ensure  => file,
  source  => 'puppet:///modules/ldap/YOUGOV-AD01-CA.rencer';
}

class {'yhost': }
class {'pipdeps': }
class {'pg91': }
class {'currentmongo': }
class {'lxc': }
