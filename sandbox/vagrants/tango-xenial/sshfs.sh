# !/bin/bash

sshfs -o "reconnect,ServerAliveInterval=10,ServerAliveCountMax=2,IdentityFile=$PWD/.vagrant/machines/default/lxc/private_key,Port=2223" vagrant@localhost: $HOME/mnts/tango-test/
