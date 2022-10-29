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


FROM nvidia/cuda:10.1-devel-ubuntu18.04

WORKDIR /home

# Install packages and register python3 (version 3.8) as python
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections && \
    apt-get update -y && apt-get install -y dialog apt-utils && \
    apt-get install -y build-essential git wget curl software-properties-common && \
    apt update && add-apt-repository ppa:deadsnakes/ppa -y && \
    apt install -y python3.8 python3.8-dev python3.8-distutils python3.8-venv && \\
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.8 get-pip.py && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.8 10 && \
    apt-get autoremove -y --purge && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install each piece of external software that Ot2Rec calls

# Install ctffind-dependencies
RUN apt-get intel-mkl && \
    apt-add-repository 'deb https://repos.codelite.org/wx3.2.0/ubuntu/ jammy universe' && \
    apt-get update && \
    apt-get install libwxbase3.2-0-unofficial \
                libwxbase3.2unofficial-dev \
                libwxgtk3.2-0-unofficial \
                libwxgtk3.2unofficial-dev \
                wx3.2-headers \
                wx-common \
                libwxgtk-media3.2-0-unofficial \
                libwxgtk-media3.2unofficial-dev \
                libwxgtk-webview3.2-0-unofficial \
                libwxgtk-webview3.2unofficial-dev \
                libwxgtk-webview3.2-0-unofficial-dbg \
                libwxbase3.2-0-unofficial-dbg \
                libwxgtk3.2-0-unofficial-dbg \
                libwxgtk-media3.2-0-unofficial-dbg \
                wx3.2-i18n \
                wx3.2-examples

# Install ctffind

RUN wget -c "https://grigoriefflab.umassmed.edu/system/tdf?path=ctffind-4.1.14.tar.gz&file=1&type=node&id=26" && \
    mv 'tdf?path=ctffind-4.1.14.tar.gz&file=1&type=node&id=26' ctffind-4.1.14.tar.gz && \
    tar xvf ctffind-4.1.14.tar.gz && \
WORKDIR /home/ctffind-4.1.14
RUN make && make install
WORKDIR /home

RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.20_RHEL7-64_CUDA10.1.sh && \
    apt install -y default-jre tcsh && \
    sh imod_4.11.20_RHEL7-64_CUDA10.1.sh

ADD . /usr/local/Ot2Rec
WORKDIR /usr/local/Ot2Rec

# Install python packages
RUN pip3 install --no-cache-dir --upgrade \
        mock pytest pytest-cov PyYAML coverage  && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +

# Install Ot2Rec from the current commit
RUN pip3 install -e . && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +
