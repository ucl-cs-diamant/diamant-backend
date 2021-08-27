#!/bin/bash

trap "echo script failed; exit 1" ERR


# install general packages
cd ~ || exit
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install apt-utils -y
sudo apt-get install build-essential git screen htop ncdu -y
sudo apt-get install python3-dev python3-venv python3-pip python3-wheel -y


# install docker
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y


# prepare docker
if [[ $(sudo docker ps -a -q) ]]; then
  sudo docker stop "$(sudo docker ps -a -q)";
  sudo docker rm "$(sudo docker ps -a -q)";
fi

#sudo docker build https://github.com/ucl-cs-diamant/docker.git#:ubuntu-gamerunner -t ubuntu-gamerunner
#sudo docker build https://github.com/ucl-cs-diamant/docker.git -t gamerunner

# todo: do the swarm manager creation and setting up service and whatever

echo "All done."
