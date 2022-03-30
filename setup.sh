#!/usr/bin/env bash

# install any software packages needed for running code or scripts on the
# ubuntu Linux image.  

# these are examples, you only need to install the packages you actually need
# if they aren't part of the default ubuntu.


apt-get install -y python3 python3-pip python3-dev
apt-get install -y g++
apt-get install -y clang-3.9
ln -s /usr/bing/clang++-3.9 /usr/bin/clang++

pip3 install -r /autograder/source/requirements.txt

# these are needed by script
apt-get install -y python3.8 python3.8-dev
python3.8 -m pip install --upgrade pyyaml
python3.8 -m pip install pytz

