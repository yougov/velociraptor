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
        timeout => "300",
    }
    
    Package {ensure => present, require => Exec [firstupdate]}

    package {
        nginx:; 
        supervisor:; 
        ruby:;
        libevent-dev:;
        vim:;
        python-software-properties:;
        curl:;
        libcurl4-gnutls-dev:;
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
    Package {provider => pip, ensure => present, require => Class [py27]}
    package { 
      mercurial:;
      virtualenv:;
    }
}


class pg91 {
    exec {
      addpgbackport:
        command => "add-apt-repository ppa:pitti/postgresql",
        require => Class [yhost];
      pgaptupdate:
        command => "apt-get update",
        timeout => "300",
        require => Exec [addpgbackport];
    }

    package {
      "postgresql-9.1":
        ensure => present,
        require => Exec [pgaptupdate];
      "postgresql-server-dev-9.1":
        ensure => present,
        require => Exec [pgaptupdate];
    }
    # TODO: Ensure that /etc/postgresql/9.1/main/pg_hba.conf is configured to
    # trust local connections.
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

package { 
  foreman:
    ensure => present,
    provider => gem,
    require => Class [yhost];
}

class {'yhost': }
class {'pipdeps': }
class {'py27': }
class {'pg91': }
