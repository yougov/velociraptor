from setuptools import setup, find_packages

setup(
    name = 'velociraptor-cli',
    description = 'Command Line Interface for Velociraptor',
    packages = find_packages(),
    author = 'Alfredo Deza',
    author_email = 'contact [at] deza.pe',
    scripts = ['bin/vr'],
    install_requires = ['tambo'],
    version = '0.0.1',
    url = 'http://bitbucket.com/yougov/velociraptor',
    license = "MIT",
    zip_safe = False,
    keywords = "commands, cli, velociraptor",
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)
