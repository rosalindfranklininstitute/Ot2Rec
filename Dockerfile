# Copyright 2021 Rosalind Franklin Institute
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


FROM nvidia/cuda:11.4.0-base-ubuntu20.04

# Install packages and register python3 as python
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections && \
    apt-get update -y && apt-get install -y dialog apt-utils unzip && \
    apt-get install -y build-essential git wget python3 python3-pip && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 10 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 10 && \
    apt-get autoremove -y --purge && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install each piece of external software that Ot2Rec calls
# Motioncor2
WORKDIR /usr/local/MotionCor2
RUN wget --no-hsts -O Motioncor2-v1.4.4.zip "https://drive.google.com/uc?export=download&id=15CwzXfqqnYE7XpkZuT94H4XjbNUDUt4B" && \
unzip Motioncor2-v1.4.4.zip && rm Motioncor2-v1.4.4.zip && \
find /usr/local/MotionCor2 -type d -print0 | xargs -0 chmod 755 && find /usr/local/MotionCor2 -type f -print0 | xargs -0 chmod 644

# ctffind4
WORKDIR /usr/local/ctffind
RUN wget -O ctffind-4.1.14-linux64.tar.gz "https://grigoriefflab.umassmed.edu/system/tdf?path=ctffind-4.1.14-linux64.tar.gz&file=1&type=node&id=26" && \
tar -xf ctffind-4.1.14-linux64.tar.gz && mv bin/ ctffind-4.1.14/ && rm ctffind-4.1.14-linux64.tar.gz && \
find /usr/local/ctffind -type d -print0 | xargs -0 chmod 755 && find /usr/local/ctffind -type f -print0 | xargs -0 chmod 644

# IMOD
WORKDIR /usr/local/imod
RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.10_RHEL7-64_CUDA10.1.sh && \
    bash imod_4.11.10_RHEL7-64_CUDA10.1.sh -dir /usr/local/imod -debian -yes && rm imod_4.11.10_RHEL7-64_CUDA10.1.sh && \
find /usr/local/imod -type d -print0 | xargs -0 chmod 755 && find /usr/local/imod -type f -print0 | xargs -0 chmod 644

# Install python packages
RUN pip3 install --no-cache-dir --upgrade \
        mock pytest pytest-cov PyYAML coverage  && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +

# Install Ot2Rec from the current commit
ADD . /usr/local/Ot2Rec
WORKDIR /usr/local/Ot2Rec
RUN pip3 install -e . && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +
