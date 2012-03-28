from fabric.api import run, sudo

def get_os_version():
    return run('cat /etc/issue')

# Don't take this as a model for how we'll arrange our code.  I just wanted
# something that would take a while so I could watch its progress.
def install_pycrypto():
    return sudo('pip install pycrypto --upgrade')

def get_date():
    return run('date')
