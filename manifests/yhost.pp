
group { "puppet": 
    ensure => "present", 
}

Exec { path => '/usr/bin:/bin:/usr/sbin:/sbin' }

# We have to update first to ensure that apt can find the
# python-software-properties package that will then let us add PPAs
class fresh_apt {
    exec {
      firstupdate:
        command => "apt-get update",
        timeout => "300",
    }
}

class yhost {
    Package {ensure => present}

    package {
        nginx:; 
        supervisor:; 
        python-pycurl:; 
        python-dev:;
        ruby:;
        libevent-dev:;
        vim:;
        python-software-properties:;
        curl:;
        rabbitmq-server:;
        libldap2-dev:;
        libsasl2-dev:;
    }
}

# TODO: Once Jason has the upstart config ready for supervisord, switch to the
# pip-installed version instead of the apt-installed one.

# TODO: ensure that supervisord's config has the line to include
# /opt/yg/procs/*/proc.conf

# As of http://projects.puppetlabs.com/issues/6527, Puppet contains native
# support for using pip as a package provider.  We can use that to provide
# newer versions of Python packages than Ubuntu provides.  It would also be
# trivial to make a ygpip provider that pulls from our cheeseshop.

class pipdeps {
    Package {provider => pip}
    package { 
      pip: # use pip to install newer pip
        ensure => latest;
      mercurial:
        ensure => present;
      virtualenv:
        ensure => latest;
    }
}


class pg91 {
    exec {
      addpgbackport:
        command => "add-apt-repository ppa:pitti/postgresql",
        require => Class [yhost];
      runaptgetupdate:
        command => "apt-get update",
        timeout => "300",
        require => Exec [addpgbackport];
    }

    package {
      "postgresql-9.1":
        ensure => present,
        require => Exec [runaptgetupdate];
      "postgresql-server-dev-9.1":
        ensure => present,
        require => Exec [runaptgetupdate];
    }
    # TODO: Ensure that /etc/postgresql/9.1/main/pg_hba.conf is configured to
    # trust local connections.
}

class py27 {
    exec {
      pythonppa:
        command => "add-apt-repository ppa:fkrull/deadsnakes";
    }

    package {
      "python2.7":
        ensure => present,
        require => Exec [pythonppa];
      "python2.7-dev":
        ensure => present,
        require => Exec [pythonppa];
    }
}

package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Class [yhost];
}

class {'fresh_apt': } -> class {'yhost': }
class {'pipdeps': }
class {'py27': }
class {'pg91': }
