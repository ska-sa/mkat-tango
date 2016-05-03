#! /bin/bash

export DEBIAN_FRONTEND=noninteractive

sed -i 's~http://archive.ubuntu.com~http://ubuntu.mirror.ac.za~' /etc/apt/sources.list
# Some silly vagrant box does not use the default
sed -i 's~http://ubuntu.mirror.lrz.de~http://ubuntu.mirror.ac.za~' /etc/apt/sources.list

apt-get update
# dictionaries-commen bug? See
# https://bugs.launchpad.net/ubuntu/+source/dictionaries-common/+bug/873551
apt-get install -y dictionaries-common 

# Virtualbox stuff
#apt-get install -y virtualbox-guest-dkms virtualbox-guest-utils virtualbox-guest-x11

# Desktop stuff
# apt-get install -y xfce4 firefox chromium-browser
# Graphical login if so inclined
# apt-get install -y xdm

# Convenience stuff
apt-get install -y wajig terminator jed screen mlocate

# Development stuff
apt-get install -y build-essential pkgconf git

# Set up basic python stuff such that pip and virtualenvs work
apt-get install -y python curl
rm -f "/tmp/get-pip.py"
curl -s -S "https://bootstrap.pypa.io/get-pip.py" -o "/tmp/get-pip.py"
python /tmp/get-pip.py
pip install virtualenvwrapper ipython
