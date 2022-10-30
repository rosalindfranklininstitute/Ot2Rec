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

WORKDIR /usr/local/Ot2Rec
COPY . .

# Install packages and register python3 (version 3.8) as python
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections && \
    apt-get update -y && apt-get install -y dialog apt-utils && \
    apt-get install -y build-essential git wget curl software-properties-common && \
    apt-get update && add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get install -y python3.8 python3.8-dev python3.8-distutils python3.8-venv && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.8 get-pip.py && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.8 10

# Install plugin dependencies

# Install ctffind-dependencies
RUN apt-get update && apt-get install -y libfftw3-dev
RUN apt-key adv --fetch-keys http://repos.codelite.org/CodeLite.asc && \
    apt-add-repository 'deb http://repos.codelite.org/wx3.0.5/ubuntu/ bionic universe' -y && \
    apt-get update && \
    apt-get install -y libwxbase3.0-0-unofficial \
                 libwxbase3.0-dev \
                 libwxgtk3.0-0-unofficial \
                 libwxgtk3.0-dev \
                 wx3.0-headers \
                 wx-common \
                 libwxbase3.0-dbg \
                 libwxgtk3.0-dbg \
                 wx3.0-i18n \
                 wx3.0-examples \
                 wx3.0-doc \
                 zlib1g-dev \
                 libjpeg-dev \
                 libtiff5-dev
# Install ctffind
RUN cd /home && wget -c "https://grigoriefflab.umassmed.edu/system/tdf?path=ctffind-4.1.14.tar.gz&file=1&type=node&id=26" && \
    mv 'tdf?path=ctffind-4.1.14.tar.gz&file=1&type=node&id=26' ctffind-4.1.14.tar.gz && \
    tar xvf ctffind-4.1.14.tar.gz && rm ctffind-4.1.14.tar.gz && cd ctffind-4.1.14 && \
    ./configure && make && make install && cd .. && rm -r ctffind-4.1.14 && cd /usr/local/Ot2Rec

# Install IMOD dependencies
RUN apt-get install -y default-jre tcsh
# Install IMOD
RUN cd /home && mkdir IMOD-4.11.20 && cd IMOD-4.11.20 && \
    wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.20_RHEL7-64_CUDA10.1.sh && \
    sh imod_4.11.20_RHEL7-64_CUDA10.1.sh -yes && cd .. && rm -r IMOD-4.11.20 && cd /usr/local/Ot2Rec

# Install Ot2Rec

# Install python packages
RUN pip3 install --no-cache-dir --upgrade \
        mock pytest pytest-cov PyYAML coverage && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +

# Install Ot2Rec from the current commit
RUN pip3 install -e . && pip3 install . && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +
