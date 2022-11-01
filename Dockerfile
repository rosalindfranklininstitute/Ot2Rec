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

# Install necessary packages
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections && \
    apt-get update -y && apt-get install -y dialog apt-utils && \
    apt-get install -y build-essential git wget curl software-properties-common && \
    apt-get update && rm -rf /var/lib/apt/lists/*

# Install miniconda
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-py38_4.12.0-Linux-x86_64.sh -b \
    && rm -f Miniconda3-py38_4.12.0-Linux-x86_64.sh

# Install plugin dependencies

#Install Savu
RUN cd /tmp && git clone https://github.com/DiamondLightSource/Savu.git && cd Savu && \
    conda install --yes --file install/savu_lite37/spec-savu_lite_latest.txt

SHELL ["conda", "run", "-n", "base", "/bin/bash", "-c"]

RUN cd /tmp/Savu && python setup.py install && cd .. && rm -r Savu && cd /usr/local/Ot2Rec
RUN conda install -y redlionfish -c conda-forge

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
RUN cd /tmp && \
    wget -O ctffind-4.1.14.tar.gz -c "https://grigoriefflab.umassmed.edu/system/tdf?path=ctffind-4.1.14.tar.gz&file=1&type=node&id=26" && \
    tar xvf ctffind-4.1.14.tar.gz && rm ctffind-4.1.14.tar.gz && cd ctffind-4.1.14 && \
    ./configure && make && make install && cd .. && rm -r ctffind-4.1.14 && cd /usr/local/Ot2Rec

# Install IMOD dependencies
RUN apt-get install -y default-jre tcsh
# Install IMOD
RUN cd /tmp && mkdir IMOD-4.11.20 && cd IMOD-4.11.20 && \
    wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.20_RHEL7-64_CUDA10.1.sh && \
    sh imod_4.11.20_RHEL7-64_CUDA10.1.sh -yes && cd .. && rm -r IMOD-4.11.20 && cd /usr/local/Ot2Rec
ENV PATH="${PATH}:/usr/local/IMOD/bin"
ARG PATH="${PATH}:/usr/local/IMOD/bin"
ENV IMOD_DIR="/usr/local/IMOD"
ARG IMOD_DIR="/usr/local/IMOD"
# Install Ot2Rec

# Install python packages
RUN pip install --no-cache-dir --ignore-installed \
        mock pytest pytest-cov PyYAML coverage && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +

# Install Ot2Rec from the current commit
RUN pip install -e . && pip3 install . && \
    rm -rf /tmp/* && \
    find /usr/lib/python3.*/ -name 'tests' -exec rm -rf '{}' +
