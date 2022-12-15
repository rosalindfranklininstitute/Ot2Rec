# Ot2Rec

![GitHub](https://img.shields.io/github/license/rosalindfranklininstitute/Ot2Rec?kill_cache=1) [![GitHub Workflow Status (branch)](https://github.com/rosalindfranklininstitute/Ot2Rec/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rosalindfranklininstitute/Ot2Rec/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/rosalindfranklininstitute/Ot2Rec/branch/main/graph/badge.svg?token=uwLz2XD7ac)](https://codecov.io/gh/rosalindfranklininstitute/Ot2Rec)

## What is Ot2Rec?
Ot2Rec is a Python suite which aims to automate the preprocessing and reconstruction workflow of (cryo-)electron tomographic images. This code is a product of the Artificial Intelligence & Informatics (AI&I) group at the [Rosalind Franklin Institute](https://www.rfi.ac.uk).

Ot2Rec was developed with three aims in mind:

- Enable mixing and matching of different software tools for each stage of image processing through to tomogram reconstruction.
- User-friendly GUI to capture user input, which is kept to a minimum
- Provide framework for performance measurement and eventually automated parameter tuning for optimum reconstruction without user intervention

## Features
- Supports a wide range of plugins (MotionCor2, IMOD, AreTomo, Savu, CTFFind4, CTFSim, RedLionfish Deconvolution)
- Runs in parallel on computer clusters
- GPU operations enabled in stages where possible
- Highly modularised API
- Software architecture supports internal and serialised metadata
- Input parameters automatically updated upon running
- Supports multiple data formats (Tiff, Mrc, EER)
- Easy integration of new plugins

## Contacts
For questions regarding Ot2Rec, please raise an [issue](https://github.com/rosalindfranklininstitute/Ot2Rec/issues).

## License
This software is licensed under the Apache License (V2). 
Copyright (C) 2021 Rosalind Franklin Institute.


***
# Installation guide

## Software requirements (external prerequisites)

- CUDA
- Motioncor2*
- CTFFind4*
- IMOD*
- AreTomo*
- Savu*
- miniconda

* for plugins

## Obtaining Ot2Rec
Ot2Rec can be obtained by cloning this repository
```
git clone https://github.com/rosalindfranklininstitute/Ot2Rec.git
```

## Installing Ot2Rec
1. You will need miniconda. If you have not yet installed miniconda yet, you can obtain it by following the instructions [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html).

2. (Optional, but recommended) Update miniconda
   ```
   conda update conda
   ```

3. Once miniconda is set up, create a virtual environment for Ot2Rec and activate the environment
   ```
   conda create --name o2r
   conda activate o2r
   ```

4. Go to the Ot2Rec folder and install Ot2Rec
   ```
   cd /path/to/Ot2Rec/
   python setup.py develop
   ```

***
# Usage guide

Please see the tutorial on our [Wiki](https://github.com/rosalindfranklininstitute/Ot2Rec/wiki/Tutorial:-Basic-reconstruction-workflow-in-Ot2Rec)

***

# Contributing to Ot2Rec

We welcome all contributions - you don't have to code to contribute. Please see our [contributing guide](https://github.com/rosalindfranklininstitute/Ot2Rec/wiki/Contributing-Guide) to get started. If you'd like to write your own plugin, we have a [guide](https://github.com/rosalindfranklininstitute/Ot2Rec/wiki/Tutorial:-How-to-write-an-Ot2Rec-plugin) to help.

***

# Citing

tbc