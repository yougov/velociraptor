group { "puppet": 
    ensure => "present", 
}

Exec { path => '/usr/bin:/bin:/usr/sbin:/sbin' }

# We have to update first to ensure that apt can find the
# python-software-properties package that will then let us add PPAs

class yhost {
    exec {
      firstupdate:
        command => "apt-get update",
        timeout => "300";
    }
    
    Package {ensure => present, require => Exec [firstupdate]}

    package {
        ruby:;
        libevent-dev:;
        vim:;
        python-software-properties:;
        curl:;
        libcurl4-gnutls-dev:;
        rabbitmq-server:;
        libldap2-dev:;
        libsasl2-dev:;
        libpcre3-dev:;
        libjpeg62-dev:;
        git-core:;
    }
}

# As of http://projects.puppetlabs.com/issues/6527, Puppet contains native
# support for using pip as a package provider.  We can use that to provide
# newer versions of Python packages than Ubuntu provides.  

class pipdeps {
    Package {provider => pip, ensure => present, require => Class [py27]}
    package { 
      mercurial:;
      virtualenv:;
      virtualenvwrapper:;
    }
}

# TODO: Make a ygpip provider that pulls from our cheeseshop.  Modify this:
# https://github.com/rcrowley/puppet-pip/blob/master/lib/puppet/provider/package/pip.rb

# TODO: Once we have a ygpip provider, switch to the
# pip-installed version instead of the apt-installed one.

class pg91 {
    exec {
      addpgbackport:
        command => "add-apt-repository ppa:pitti/postgresql",
        require => Class [yhost];
      pgaptupdate:
        command => "apt-get update",
        timeout => "300",
        require => Exec [addpgbackport];
      pgrestart:
        command => "/etc/init.d/postgresql restart",
        require => File ['pg_hba.conf'];
    }

    package {
      "postgresql-9.1":
        ensure => present,
        require => Exec [pgaptupdate];
      "postgresql-server-dev-9.1":
        ensure => present,
        require => Exec [pgaptupdate];
    }

    file { 'pg_hba.conf':
      path    => '/etc/postgresql/9.1/main/pg_hba.conf',
      ensure  => file,
      require => Package['postgresql-9.1'],
      source  => 'puppet:///modules/postgres/pg_hba.conf';
    }
}

class py27 {
    exec {
      pythonppa:
        command => "add-apt-repository ppa:fkrull/deadsnakes",
        require => Class [yhost];
      pyaptupdate:
        command => "apt-get update",
        timeout => "300",
        require => Exec [pythonppa];
      pip27:
        command => "easy_install-2.7 pip",
        require => Package ["python-distribute-deadsnakes"];
    }

    Package {ensure => present, require => Exec [pyaptupdate]}

    package {
      "python2.7":;
      "python2.7-dev":;
      "python-distribute-deadsnakes":;
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

class gemsrc {
    exec {
      install_gemsrc:
        command => '/tmp/install_gems.sh',
        require => File ['install_gems.sh'];
    }

    file { 'install_gems.sh':
        path => '/tmp/install_gems.sh',
        ensure => file,
        mode => 755,
        source => 'puppet:///modules/gemsrc/install_gems.sh';
    }
}

package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Class [gemsrc];
}

# Include the self-signed SSL cert that yg.ldap needs to make secure
# connections to our domain controllers.
file { 'ldap_cert':
  path    => '/etc/ssl/YOUGOV-AD01-CA.rencer',
  ensure  => file,
  source  => 'puppet:///modules/ldap/YOUGOV-AD01-CA.rencer';
}

class {'yhost': }
class {'gemsrc': }
class {'pipdeps': }
class {'py27': }
class {'pg91': }
class {'currentmongo': }
