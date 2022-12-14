#!/bin/bash

version=$1

# Change version number in construct.yaml
sed -i -r 's/(^s*version:) ([0-9.]+)/\1 '$version'/' construct.yaml
sed -i -r 's/(- Ot2Rec) ([0-9.]+)/\1 '$version'/' construct.yaml

# Change version number in setup.py
sed -i -r "s/(version=)('[0-9.]+')/\1'"$version"'/" setup.py

# Change version number in conda-build/meta.py
sed -i -r 's/(version:) ([0-9.]+)/\1 '$version'/' conda-build/meta.yaml

# Stage changed config files
git add construct.yaml setup.py conda-build/meta.yaml
