#! /bin/bash

export DEBIAN_FRONTEND=noninteractive

apt-get -y install subversion \
	xauth # allows ssh -X to work
apt-get -y install mysql-server mysql-client
apt-get -y install  tango-common tango-db tango-starter tango-test python-pytango\
        libboost-python-dev
#add-apt-repository 'deb http://ppa.launchpad.net/tango-controls/core/ubuntu precise main'
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A8780D2D6B2E9D50
sudo apt-key update
apt-get -y update
apt-get -y install libtango-java

mkdir -p ~vagrant/src
sudo chown vagrant.vagrant ~vagrant/src
#su vagrant -c 'svn co https://tango-cs.svn.sourceforge.net/svnroot/tango-cs/share/fandango/trunk/fandango ~vagrant/src/fandango'

su vagrant -c 'git clone -b add-setup.py  https://github.com/ska-sa/fandango.git ~vagrant/src/fandango'
pip install -e ~vagrant/src/fandango

# apt-get -y install libboost-python-dev mysql-server tango-db tango-test libtango8-dev
# apt-get -y install python-taurus


# Use --egg to avoid "error: option --single-version-externally-managed not recognized"
# error
#pip install --egg PyTango

# Fix rediculous java font over X stuff

BASHRC=~vagrant/.bashrc
if ! grep -q _JAVA_OPTIONS $BASHRC
then
    echo export _JAVA_OPTIONS="-Dawt.useSystemAAFontSettings=on" >> $BASHRC
fi
