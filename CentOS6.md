# MAVEDB installation notes

MAVEDB is Django website with Postgres as the backend. Its purpose is to allow 
researchers to deposit and retrieve deep mutational scanning datasets. This file 
provides step-by-step instructions for installing MAVEDB starting with the 
`CentOS-6.9-x86_64-minimal.iso` downloaded from 
[CentOS.org](http://isoredirect.centos.org/centos/6/isos/x86_64/). To set up 
MAVEDB on an Amazon EC2 instance, use the 
[Centos 6 HVM image](https://aws.amazon.com/marketplace/pp/B00A6KUVBW) from the
AWS marketplace.

## Notes on networking

Users running CentOS 6 in VirtualBox or a similar VM setup may find that the 
network interface is not enabled by default. See the 
[CentOS wiki](https://wiki.centos.org/FAQ/CentOS6#head-b67e85d98f0e9f1b599358105c551632c6ff7c90) 
for detailed instructions on enabling `eth0`.

Users running in a local VM or who want to rely on AWS security groups may want 
to disable all `iptables` firewall rules using the following script:

    #!/bin/bash
    
    # Script to clear all firewall rules for iptables and accept all traffic
    # Based on https://www.digitalocean.com/community/tutorials/how-to-list-and-delete-iptables-firewall-rules
    
    # Set the default policies for each of the built-in chains to ACCEPT
    
    sudo iptables -P INPUT ACCEPT
    sudo iptables -P FORWARD ACCEPT
    sudo iptables -P OUTPUT ACCEPT
    
    # Flush the nat and mangle tables, flush all chains (-F), and delete all non-default chains (-X):
    
    sudo iptables -t nat -F
    sudo iptables -t mangle -F
    sudo iptables -F
    sudo iptables -X
    
    # Save changes
    sudo service iptables save


## Updating yum and adding basic dependencies

Since this is a fresh installation of CentOS, first update the package manager 
and add some basic dependencies.

    sudo yum -y update
    sudo yum -y install epel-release
    sudo yum -y install yum-utils
    sudo yum -y groupinstall development
    sudo yum -y install zlib-devel
    sudo yum -y install wget
    sudo yum -y install httpd-devel

## Adding Python 3.4

Python 3.4 is the earliest version of Python supported by the version of Django 
(1.11) that we are using. We will also need `pip` to install `virtualenv`. All 
further Python packages will be added within a new virtual environment that 
contains the project.

    sudo yum -y install python34 python34-devel python34-setuptools
    cd /usr/lib/python3.4/site-packages/
    sudo python3 easy_install.py pip
    sudo pip3 install virtualenv

## Installing Postgres using yum

We need a newer version of PostgreSQL than is available on `yum`, so we can 
follow the 
[guide on postgresl.org](https://wiki.postgresql.org/wiki/YUM_Installation). 
Commands are as follows.

    # add 'exclude=postgresql*' statements to [base] and [updates]
    sudo vi /etc/yum.repos.d/CentOS-Base.repo

    sudo yum -y install https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-6-x86_64/pgdg-centos96-9.6-3.noarch.rpm
    sudo yum -y install postgresql96-server postgresql96-contrib

This installation process didn't add some useful tools to the path so we can 
add them ourselves.

    sudo /usr/sbin/update-alternatives --install /usr/bin/pg_ctl pgsql-pg_ctl /usr/pgsql-9.6/bin/pg_ctl 960
    sudo /usr/sbin/update-alternatives --install /usr/bin/pg_isready pgsql-pg_isready /usr/pgsql-9.6/bin/pg_isready 960

### Postgres server setup

This section gets the Postgres install ready for the Django project. First, set 
up and started the server.

    sudo service postgresql-9.6 initdb
    sudo chkconfig postgresql-9.6 on
    sudo service postgresql-9.6 start

Next, log in as the postgres user and added the database at the prompt.

    sudo su - postgres
    psql

The following commands create the database and the user Django is expecting. The 
`mave_admin` user name and credentials are specified in the settings file 
located in the `mavedb/settings/` directory. Choose or create the correct 
settings file for the deployment type (e.g. `mavedb/settings/local.py` for a 
local install).

    CREATE DATABASE mavedb;
    CREATE USER mave_admin WITH PASSWORD 'abc123';
    ALTER ROLE mave_admin SET client_encoding to 'utf8';
    ALTER ROLE mave_admin SET default_transaction_isolation TO 'read committed';
    ALTER ROLE mave_admin SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE mavedb TO mave_admin;

There were issues with authentication using `ident` so I use `md5` instead.

    # change the 'ident' lines to 'md5'
    vi /var/lib/pgsql/9.6/data/pg_hba.conf
    pg_ctl restart

Depending on the details of your installation, more sophisticated access 
control may be necessary.

## Installing pandoc

The latest version of `pandoc` that was available through `yum` is 1.9 and it 
doesn't support some of the features we need. This step builds `pandoc` from 
source using `stack`. The `--flag pandoc:embed_data_files` option creates a 
relocatable binary with the default templates included. The last command moves 
the executable, and the `.stack-work` directory can be deleted to save space.

    wget -qO- https://get.haskellstack.org/ | sh
    wget https://hackage.haskell.org/package/pandoc-1.19.2.1/pandoc-1.19.2.1.tar.gz
    tar xf pandoc-1.19.2.1.tar.gz
    cd pandoc-1.19.2.1
    stack setup
    stack build --flag pandoc:embed_data_files
    mv .stack-work/install/x86_64-linux-gmp4/lts-7.14/8.0.1/bin/pandoc /usr/local/bin/

This was by far the most time consuming part of the whole process. Users on a 
low-memory EC2 instance will not have enough memory to build `pandoc`, but it 
can be copied from another system if it was built with 
`--flag pandoc:embed_data_files`.

## Setting up the MAVEDB virtual environment

Having installed all the dependencies, we can create and activate the Python 
virtual environment and install dependencies.

    mkdir ~/mavedb_project
    cd ~/mavedb_project
    virtualenv mavedb_venv
    source mavedb_venv/bin/activate

# Documentation updated for AWS up to this point

## Installing MAVEDB

Next I downloaded the source code for the project (note: this is in a private 
GitHub repository) and set up the database. Database login details are stored 
in `'~/mavedb_project/mavedb/mavedb/settings.py'`.

    git clone -b develop https://afrubin@github.com/fowlerlab/mavedb
    pip3 install -r mavedb/requirements.txt
    cd mavedb
    python manage.py migrate

Since the website contains static images, these need to be placed in a location 
where Apache can find them.

    python manage.py collectstatic
    python manage.py createlicences
    python manage.py createreferences

### Starting the server

We can start now the server using the `mod_wsgi-express` wrapper. The `mod_wsgi` 
[documentation pages](http://modwsgi.readthedocs.io/en/develop/index.html) have 
details about how to install it from source and modify Apache's settings. The 
following command can successfully start the server after a reboot.

    cd ~/mavedb_project
    source mavedb_venv/bin/activate
    mod_wsgi-express start-server \
        --working-directory mavedb \
        --url-alias /static mavedb/static \
        --application-type module mavedb.wsgi
