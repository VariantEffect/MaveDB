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
    sudo yum -y install hg


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
    ALTER USER mave_admin CREATEDB;

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


## Installing and configuring RabbitMQ
Using celery to run long running processes requires the broker-messaging backend RabbitMQ.
Installing RabbitMQ requires the installation of Erlang as a dependency. RabbitMQ has 
provided a minial dependency-free version of Erlang. You will need to add an additional
repository by following the CentOS 6 instructions [here](https://github.com/rabbitmq/erlang-rpm#bintray-yum-repositories). 
To summarize:

	# In /etc/yum.repos.d/rabbitmq-erlang.repo
	[rabbitmq-erlang]
	name=rabbitmq-erlang
	baseurl=https://dl.bintray.com/rabbitmq/rpm/erlang/20/el/6
	gpgcheck=1
	gpgkey=https://dl.bintray.com/rabbitmq/Keys/rabbitmq-release-signing-key.asc
	repo_gpgcheck=0
	enabled=1

Once you have added the additional repository you can install erlang by invoking the `yum` command

    sudo yum -y install erlang
    
There are several ways to install the `rabbitmq-server`. The quickest is to download
the `3.7.5` rpm

	wget https://dl.bintray.com/rabbitmq/all/rabbitmq-server/3.7.5/rabbitmq-server-3.7.5-1.el6.noarch.rpm
   
If you need a later version, you can check the available rps [here](https://www.rabbitmq.com/install-rpm.html#install-rabbitmq).
Once you have downloaded the rpm, follow [these](https://www.rabbitmq.com/install-rpm.html#install-rabbitmq) instructions. To
summarize

	rpm --import https://www.rabbitmq.com/rabbitmq-release-signing-key.asc
	sudo yum -y install rabbitmq-server-3.7.5-1.el6.noarch.rpm

Once the installation has completed, you will need to start the RabbitMQ service. By default,
this service listens on port 5672, which you may need to configure. To start the daemon by default 
when the system boots, as an administrator run

    sudo chkconfig rabbitmq-server on
    
As an administrator, you can start or stop the service with:

	sudo /sbin/service rabbitmq-server start
	sudo /sbin/service rabbitmq-server stop
	
For additional information see [here](https://www.rabbitmq.com/install-rpm.html#running-rpm).


## Setting up the MAVEDB virtual environment
Having installed all the dependencies, we can create and activate the Python 
virtual environment and install dependencies.

    mkdir ~/usr/local/venvs/
    cd ~/usr/local/venvs/
    sudo chown centos:centos -R /usr/local/venvs/
    virtualenv mavedb
    source mavedb/bin/activate
    
**Warning:** Do not run virtualenv with `sudo` as this might initialize the
environment with the incorrect Python version.


## Installing MAVEDB
Next I downloaded the source code for the project (note: this is in a private 
GitHub repository) and set up the database. Database login details are stored 
in `settings/secrets.json`. This file is not tracked by GitHub. First create
the directories:

    sudo mkdir /usr/local/webapps/
    sudo mkdir /usr/local/webapps/logs

The user responsible for these directories should be the owner. In our case this
was the default `centos` user.

    sudo chown centos:centos -R /usr/local/webapps/

To clone the project. **Warning: Do not install the requirements with `sudo` as this
will use the system python, and not the one in your mavedb environment. This
will cause issues with mod-wsgi and Apache later on.**

    git clone -b develop https://afrubin@github.com/fowlerlab/mavedb
    pip3 install -r mavedb/requirements.txt
    cd mavedb
    python manage.py migrate

Note you will need to create the `settings/secrets.json` file following the format:

    {
      "orcid_key": "", 
      "orcid_secret": "",
      "secret_key": <django-generated private key>,
      "database_user": "mave_admin",
      "database_password": "abc123",
      "database_host": "localhost",
      "database_port": "",
      'base_url": ""
    }
    
You can generate a random key using the following code snippet in a python shell:

    from django.utils.crypto import get_random_string
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    get_random_string(256, chars)

Since the website contains static images, these need to be placed in a location 
where Apache can find them.

    python manage.py migrate --settings=<optional|default:settings.production>
    python manage.py createlicences --settings=<optional|default:settings.production>
    python manage.py createreferences --settings=<optional|default:settings.production>
    python manage.py collectstatic --settings=<optional|default:settings.production>
    
Once these have been run the log files should have been created. There were permission issues 
when Apache tries to write to the `logs` folder. Ensure that were resolved by 
giving `rwx` permission to anyone. This is not ideal in a production environment however.

    sudo chown 777 -R /usr/local/webapps/logs/


## Configuring Celery
Running celery as a daemon process will requrie additional configuration. First
copy the celeryd configuration file (no extension) to `/etc/default/celeryd`. Next
you will need to copy the celeryd bash script to `/etc/init.d/celeryd`. You may
need to make the celeryd bash script executable
       
    sudo cp /usr/local/webapps/mavedb/celeryd /etc/default/celeryd
    sudo cp /usr/local/webapps/mavedb/celeryd.sh /etc/init.d/celeryd
	sudo chmod 755 /etc/init.d/celeryd
	sudo chown root:root /etc/init.d/celeryd
	
Running the script will require you to create an new unprivileged user named `celery`

	sudo adduser -r celery
	
You will also need to create a group `celery` which has read permissions on the mavedb
app directory `/usr/local/webapps/mavedb` and then add user `celery` to this group. This is
required so that tasks can be discovered by the daemon.
	
You may also need to grant write privileges for the celery user to the log 
default directories

	sudo chown -R celery:celery /var/log/celery/
	sudo chown -R celery:celery /var/run/celery/ 
	
To use the celery script

	sudo /etc/init.d/celeryd {start|stop|force-reload|restart|try-restart|status}

## Selenium and Geckodriver
Geckodriver needs to be on the system path before being able to run the webtests. Download
and mv geckodriver to `/usr/local/bin`


## Jenkins, Selenium and Xbvf (In-progress)
Jenkin can be configured to periodically run a complete build-test whenever changes
are made to the development branch. First install Jenkins

```bash
sudo wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat/jenkins.repo
sudo rpm --import https://jenkins-ci.org/redhat/jenkins-ci.org.key
sudo yum -y update
sudo yum install jenkins
```


## Issues with SELinux
SElinux restricted Apache's access to the mavedb project files, mavedb log files and the pandoc binary. 
I had to run these two commands on the mavedb project folder, log folder and non-recusrively 
for the pandoc binary in `/usr/local/bin`. Make sure the log file has already
been created. You can do this by first spinning up the local server via
`python manage.py runserver --settings=settings.local`.

    sudo semanage fcontext -a -t httpd_sys_rw_content_t '/usr/local/webapps/mavedb(/.*)?'
    sudo restorecon -R -v /usr/local/webapps/mavedb

    sudo semanage fcontext -a -t httpd_sys_rw_content_t '/usr/local/webapps/logs(/.*)?'
    sudo restorecon -R -v /usr/local/webapps/logs
    
    sudo semanage fcontext -a -t httpd_sys_rw_content_t '/usr/local/bin/pandoc'
    sudo restorecon -v /usr/local/bin/pandoc

Additonally run this command to allow connections on port 80
    
    sudo setsebool -P httpd_can_network_connect 1


## Quick webserver spin-up
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
        

## Server Daemonization and Apache config
To install the mod_wsgi-express module run the following comand with the mavedb
environment activated.
    
    sudo chown centos:centos /usr/lib64/httpd/modules/
    mod_wsgi-express install-module # note the install path name
    sudo chown root:root /usr/lib64/httpd/modules/

Open `/etc/httpd/conf/httpd.conf` and paste the following contents to the
bottom of the file:

    LoadModule wsgi_module modules/mod_wsgi-py34.cpython-34m.so
    WSGISocketPrefix run/wsgi
    WSGIDaemonProcess mavedb python-path=/usr/local/webapps/mavedb:/usr/local/venvs/mavedb/lib/python3.4/site-packages
    WSGIProcessGroup mavedb
    
    Alias /static/ /usr/local/webapps/mavedb/static/
    
    <Directory /usr/local/webapps/mavedb/static>
        Allow from all
    </Directory>
    
    <Directory /usr/local/webapps/mavedb/media>
        Allow from all
    </Directory>
    
    WSGIScriptAlias / /usr/local/webapps/mavedb/mavedb/wsgi.py
    
    <Directory /usr/local/webapps/mavedb/mavedb>
        <Files wsgi.py>
            Allow from all
        </Files>
    </Directory>

Make sure to replace `mod_wsgi-py34.cpython-34m.so` with your specific mod-wsgi module file
name.


# .bashrc Time-Savers
You can copy these commands into your `~/.bashrc` file. 
Make sure to run `source ~/.bashrc` to load the changes into your current shell
session.

    export DJANGO_SETTINGS_MODULE=settings.<staging or production>
    alias mavedbenv='source /usr/local/venvs/mavedb/bin/activate'
    alias update-mavedb='cd-mavedb; sudo git pull; sudo apachectl restart; cd $OLDPWD'
   
    alias mavedblog='sudo vi /usr/local/webapps/logs/mavedb.log'
    alias httperrorlog='sudo vi /var/log/httpd/error_log'
    alias httpaccesslog='sudo vi /var/log/httpd/access_log'
    alias celerylog='sudo vi /var/log/celery/worker1.log'
    
    alias edit-celerycfg='sudo vi /etc/default/celeryd'
    alias edit-celeryinit='sudo vi /etc/init.d/celeryd'
    alias run-celery='sudo /etc/init.d/celeryd'
    alias run-rabbitmq='sudo /sbin/service rabbitmq-server'
        
    alias cd-mavedb='cd /usr/local/webapps/mavedb/'
    alias cd-mavedb-logs='cd /usr/local/webapps/logsv/'
    alias cd-rmq-logs='cd /var/log/rabbitmq/'
    alias cd-celery-logs='cd /var/log/celery/'
    
