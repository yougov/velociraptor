# TODO: Use includes for all the stuff that's common between this and the
# ydevhost manifest, instead of repeating here.

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
      supervisor_reload:
        command => "supervisorctl reload",
        require => File ['supervisord.conf'];
    }
    
    Package {ensure => present, require => Exec [firstupdate]}

    package {
        supervisor:; 
        ruby:;
        libevent-dev:;
        vim:;
        curl:;
        libcurl4-gnutls-dev:;
        libldap2-dev:;
        libsasl2-dev:;
        libpcre3-dev:;
        libjpeg62-dev:;
        git-core:;
    }

    # ensure that supervisord's config has the line to include
    # /opt/yg/procs/*/proc.conf
    file { 'supervisord.conf':
      path    => '/etc/supervisor/supervisord.conf',
      ensure  => file,
      require => Package['supervisor'],
      source  => 'puppet:///modules/supervisor/supervisord.conf';
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

    file { '.bashrc':
        path => '/home/vagrant/.bashrc',
        ensure => file,
        source => 'puppet:///modules/home/bashrc';
    }
}

# TODO: Make a ygpip provider that pulls from our cheeseshop.  Modify this:
# https://github.com/rcrowley/puppet-pip/blob/master/lib/puppet/provider/package/pip.rb

# TODO: Once we have a ygpip provider, switch to the
# pip-installed version instead of the apt-installed one.


# Define a 'ppa' resource type.  With this, your classes can declare the need
# for ppa repositories to be installed, like this:
#    ppa {
#      "pitti/postgresql":;
#    }
package {
    python-software-properties: ensure => present;
}
define ppa($ppa = "$title", $ensure = present) {

  case $ensure {
    present: {

        exec { $ppa:
            command => "add-apt-repository ppa:$ppa;apt-get update",
            require => Package["python-software-properties"];
        }

        # TODO: add ability to check if PPA is installed before running the
        # above.  Might require writing some Ruby to look at files in
        # /etc/apt/sources.list.d/
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

class newredis {
    ppa {
        "rwky/redis":;
    }

    package { 'redis-server':
        ensure => present,
        require => Ppa["rwky/redis"];
    }
}

class pg91 {
    ppa {
        "pitti/postgresql":;
    }

    package {
      "postgresql-9.1":
        ensure => present,
        require => Ppa["pitti/postgresql"];
      "postgresql-server-dev-9.1":
        ensure => present,
        require => Ppa["pitti/postgresql"];
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

class py27 {
    ppa {
        "fkrull/deadsnakes":;
    }

    Package {ensure => present, require => Ppa["fkrull/deadsnakes"]}

    package {
      "python2.7":;
      "python2.7-dev":;
      "python-distribute-deadsnakes":;
    }

    exec {
      pip27:
        command => "easy_install-2.7 pip",
        require => Package ["python-distribute-deadsnakes"];
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

package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Class [yhost];
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
class {'py27': }
class {'pg91': }
class {'currentmongo': }
class {'newredis': }
