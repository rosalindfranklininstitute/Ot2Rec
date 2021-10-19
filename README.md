# Ot2Rec

![GitHub](https://img.shields.io/github/license/rosalindfranklininstitute/Ot2Rec?kill_cache=1) [![GitHub Workflow Status (branch)](https://github.com/rosalindfranklininstitute/Ot2Rec/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rosalindfranklininstitute/Ot2Rec/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/rosalindfranklininstitute/Ot2Rec/branch/main/graph/badge.svg?token=uwLz2XD7ac)](https://codecov.io/gh/rosalindfranklininstitute/Ot2Rec)

## What is Ot2Rec?
Ot2Rec is a Python suite which aims to automate the preprocessing and reconstruction workflow of (cryo-)electron tomographic images. This code is a product of the Artificial Intelligence & Informatics (AI&I) group at the [Rosalind Franklin Institute](https://www.rfi.ac.uk).

Initially built with the principle of least privilege, Ot2Rec works as a wrapper suite of the batch version of IMOD and takes the user through the data processing workflow with a minimal amount of human intervention required. This allows smooth transitions between processing stages, and results in overall speed-up when compared with the fully manual counterpart of the same workflow.

## Features
- Preprocessing of tomographic data with _MotionCor2_ and _ctffind_
- Image reconstruction and tomogram generation with _IMOD_
- Runs in parallel on computer clusters
- GPU operations enabled in stages where possible
- Highly modularised API
- Software architecture supports internal and serialised metadata
- Input parameters automatically updated upon running
- Supports multiple data formats (TIFFs / MRCs)
- Easy integration of new plugins

## Contacts
For questions regarding Ot2Rec, please feel free to contact developer at [neville.yee@rfi.ac.uk](mailto:neville.yee@rfi.ac.uk).

## License
This software is licensed under the Apache License (V2). 
Copyright (C) 2021 Rosalind Franklin Institute.


***
# Installation guide

## Software requirements (external prerequisites)
* CUDA
* Motioncor2
* ctffind
* IMOD
* miniconda

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

## 0. Overview of functionality
Ot2Rec is capable of carrying out the following tasks:
1. Creating new project and collecting raw data
2. Performing motion correction of raw images
3. Estimating contrast transfer function (CTF) of each dataset (tilt-series)
4. Creating individual stacks for each tilt-series and aligning the stacks
5. Reconstructing the aligned stacks to form final tomograms

Operations of each task will be explained in details below.

The basic format of the commands with which Ot2Rec functions are called is
```
o2r.TASK.<operation> project_name
```
where the `TASK` parameter is one of the following

TASK | Description
---- | -----------
new | Initialising a new project
get_master | Collect raw data and create master metadata file
mc | Motion correct images from specified tilt-series
ctffind | Estimate tilt-series CTF
align | Create stacks and align them
recon | Reconstruct aligned stacks
stats | Output reconstruction quality statistics

The task-specific operations (`<operation>` in the command) will be discussed in the respective sections.

## 1. New project and data collection
### Creating new project
To start a new project, it is recommended to create a new folder for the project (which is called `demo` here) specifically. In the project folder `/path/to/demo/`, there should be a subfolder (called `raw` here) which holds all the raw images.

In the `demo` folder, create a new folder named `processing` in which all image processing will be done. 
```
cd /path/to/demo
mkdir processing
```
The benefit of creating a separate folder for processing is that the outputs will not be mixed with the inputs. The project folder structure should now look like this:
```
/path/to/demo/
   |
   |---raw/
       |---(images)
   |---processing/
```   

### Creating project master configuration file
In the `processing` folder, run Ot2Rec for the first time to initialise the project. 
```
cd processing
o2r.new demo
```
The argument `demo` in the second command determines the name of the project.  
**(Warning: The project name is used throughout the processing stages and is used as the handle for file checking. DO NOT CHANGE AFTER INITIALISATION.)**

There should now be a config file named `demo_proj.yaml`. Open the file using any text editor. There should be 6 lines in the file

```
source_folder: ../raw/
TS_folder_prefix: '*'
file_prefix: '*'
image_stack_field: 1
image_tiltangle_field: 3
source_TIFF: true
```

### List of Parameters
Parameters | Descriptions 
 --- | --- 
**`source_folder`** | The path to the folder where the raw images are stored.
**`TS_folder_prefix`** | The _common_ prefix of the folders holding the raw images. For instance, if the folders for the tilt-series are named `demo_01`, `demo_02` etc., then `TS_folder_prefix` = `demo`. <br>If all raw images are in the same folder (i.e. not in individual tilt-series level subfolders), `TS_folder_prefix` = `''`. <br>**(Note: The trailing underscore is not necessary. Ot2Rec uses underscores as field separators by default.)**
**`file_prefix`** | The prefix in the filenames of the raw images, which is recommended to match with the Ot2Rec project name to avoid confusions. <br>For example, if an image in tilt series 1 (taken at the sample tilt angle -60 degrees) has the filename `demo_01_0001_-60.0.tif`, with `01` being the tilt series index, then `file_prefix` = `demo`.
**`image_stack_field`** and **`image_tiltangle_field`** | Where to find the _tilt-series number_ and the _tilt angles_ from the image file names. Fields start counting from **after the prefix.** <br>In the previous example, the filename is `TS_01_0001_-60.0.tif`, with `01` being the tilt series index, `0001` the index of image in the stack, and `-60.0` the tilt angle, then `image_stack_field` = 0 and `image_tiltangle_field` = 2. <br>**(Note: the field numbers obey the Python indexing rule, where the first field has index 0.)**  
**`source_TIFF`** | Whether the raw images are in the TIFF format. If set to `false`, the program automatically assumes the images are MRCs.

### Creating project master metadata
Now that the project master config file has been set up, the next step will be to collect the raw images and compile a master metadata for the entire project. To do this, simply use the command
```
o2r.get_master demo
```
and you should get a `demo_master_md.yaml` file. <br>***(WARNING: This file contains information (raw path, tilt series number, sample tilt angle) about the raw images being collected, and should not be altered manually.)***


## 2. Motion Correction
After creating the master metadata, the next step will be correct for the motion during image acquisition. Ot2Rec uses the external code MotionCor2 to do this. The program module must be loaded before being executed:
```
module load motioncor2
```


### Creating configuration file
To create the configuration file for MotionCor2, run the following command:
```
o2r.mc.new demo
```
which should produce the file `demo_mc2.yaml`, whose contents are listed below:
```
System:
    process_list: []
    output_path: ./motioncor/
    output_prefix: demo
    use_gpu: auto
    jobs_per_gpu: 2
    gpu_memory_usage: 1
    source_TIFF: true
MC2:
    MC2_path: /opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110
    gain_reference: nogain
    pixel_size: 0.815
    desired_pixel_size: 1.63
    discard_frames_top: 1
    discard_frames_bottom: 0
    tolerance: 0.5
    max_iterations: 10
    patch_size:
    - 5
    - 5
    - 20
    use_subgroups: true
```

Parameters are categorised into two blocks, namely `System` and `MC2`. The `System` block tells Ot2Rec what files are processed and how much computational resource to use, whereas the `MC2` block contains essential parameters for MotionCor2 to satisfactorily correct the motion-induced artefacts.  
(**NB. Parameters in configuration files are categorised in blocks. Throughout this document the parameters will be presented in the format of `<block>.<parameter>`. For instance, the `process_list` parameter above will be presented in this document as `System.process_list`.**)

### List of Parameters
Parameters | Descriptions 
 --- | --- 
**`System.process_list`** | A list of indices of all tilt-series which can be motion-corrected currently. The default list is determined directly from the master metadata file. <br>**Processing tilt-series whose numbers are not in the default list will lead to errors.**
**`System.output_path`** | The path to the folder in which the motion-corrected images will be placed. The folder will be created if it does not exist.
**`System.output_prefix`** | The prefix of the filenames of the motion-corrected images, which is by default same as that of the raw images.
**`System.use_gpu`** | Determines whether to use GPU for acceleration. By default, it is set to `auto` for automatic detection of available GPU(s). If GPU is not to be used, set the option to `False`.
**`System.jobs_per_gpu`** | Determines the number of images processed in parallel by each GPU.
**`System.gpu_memory_usage`** | Determines how much GPU memory is used by MotionCor2.
**`System.source_TIFF`** | Determines whether the raw images are in TIFF or MRC format. <br>**This parameter is directly read from the master configuration file so should not need changing.**
--- | ---
**`MC2.MC2_path`** | The path to the folder where MotionCor2 is installed.
**`MC2.gain_reference`** | The path to the gain reference file. If no file is provided, set this parameter to `nogain`
**`MC2.pixel_size`** | The pixel size (in angstroms) of the _raw images_ which can be obtained by using the IMOD `header` command on any of the raw images.
**`MC2.desired_pixel_size`** | The pixel size (in angstroms) of the output (i.e. motion-corrected) images.
**`MC2.discard_frames_top`** | The number of _initial_ frames to be deleted from the raw image stacks for removal of potential artefacts.
**`MC2.discard_frames_bottom`** | The number of _trailing_ frames to be deleted from the raw image stacks.
**`MC2.tolerance`** | The threshold of alignment errors (in pixels).
**`MC2.max_iterations`** | The maximum number of iterations beyond which alignment would terminate even if convergence is not reached.
**`MC2.patch_size`** | The patch dimensions used in the alignment. A `[m, n]` patch_size would mean the image is to be divided into (m x n) patches. A third number can be added to specify the percentage of overlap between successive patches. For instance, `[5, 5, 20]` (default) means the image would be divided into 5x5 patches, with each patch having 20% overlapping with its neighbours _in every dimension_.
**`MC2.use_subgroups`** | Instructs MotionCor2 to divide the input stack into subgroups and align the sum of the subgroups instead of individual frames.


### Running MotionCor2
With the configuration file `demo_mc2.yaml` created, we can run MotionCor2 by using the the command
```
o2r.mc.run demo
```

At the end of the process, there should be another metafile `demo_mc2_md.yaml`.
<br>***(WARNING: This file will be used in later processing stages. DO NOT MANUALLY CHANGE ITS CONTENTS.)***


## 3. CTF estimation
To estimate the defocus and hence the contrast transfer function (CTF) of the images, Ot2Rec uses the code CTFFind4.
<br>**(Note: This step is optional. The image reconstruction pipeline will not be affected if this step is omitted.)**

To use CTFFind4, the appropriate module must be loaded beforehand:
```
module load ctffind
```

### Creating configuration file
To create the configuration file for CTFFind4, run the following command:
```
o2r.ctffind.new demo
```
which should produce the file `demo_ctffind.yaml`, whose contents are listed below:
```
System:
    process_list: []
    output_path: ./ctffind/
    output_prefix: TS
    ctffind_all: true
ctffind:
    ctffind_path: /opt/lmod/modules/ctffind/4.1.14/bin/ctffind
    pixel_size: 1.63
    voltage: 300.0
    spherical_aberration: 2.7
    amp_contrast: 0.8
    amp_spec_size: 512
    resolution_min: 30.0
    resolution_max: 5.0
    defocus_min: 5000.0
    defocus_max: 50000.0
    defocus_step: 500.0
    astigm_type: null
    exhaustive_search: false
    astigm_restraint: false
    phase_shift: false
```

### List of Parameters
Parameters | Descriptions 
 --- | --- 
**`System.process_list`** | (See above)
**`System.output_path`** | (See above)
**`System.output_prefix`** | (See above)
**`System.ctffind_all`** | If set to `true`, CTF will be estimated for _all_ images in the tilt-series specified in `System.process_list`. If set to `false`, CTF will be estimated only for the image with tilt-angle closest to 0. <br>**(Note: must be set to `true` if user wants to use the _per-image_ CTF to calculate the per-image PSF for deconvolution.)**
--- | ---
**`ctffind.ctffind_path`** | The path to the folder where CTFFind4 is installed.
**`ctffind.pixel_size`** | Pixel size (in angstroms) of the motion-corrected images.
**`ctffind.voltage`** | Voltage (in keV) of the electron beam.
**`ctffind.spherical_aberration`** | Spherical aberration (in mrads) of the objective lens
**`ctffind.amp_contrast`** | Relative amplitude contrast w1 (0 <= w1 <= 1)
**`ctffind.amp_spec_size`** | Size of spectrum (in pixels)
**`ctffind.resolution_min`** | Minimum resolution in target function (in angstroms)
**`ctffind.resolution_max`** | Maximum resolution in target function (in angstroms)
**`ctffind.defocus_min`** | Lower bound of initial defocus search (in angstroms)
**`ctffind.defocus_max`** | Upper bound of initial defocus search (in angstroms)
**`ctffind.defocus_step`** | Step size of initial defocus search (in angstroms)
**`ctffind.astigm_type`** | Type of astigmatism. **(Best kept as null)**
**`ctffind.exhaustive_search`** | Turns on exhaustive search algorithm for defocus if set to `true`
**`ctffind.astigm_restraint`** | Restraint on astigmatism (in angstroms)
**`ctffind.phase_shift`** | Estimates phase shift if set to `true`

### Running CTFFind4
With the configuration file `demo_ctffind.yaml` created, we can run CTFFind4 by using the the command
```
o2r.ctffind.run demo
```

At the end of the process, there should be a new metafile `demo_ctffind_md.yaml`. <br>***(WARNING: This file will be used in later processing stages. DO NOT MANUALLY CHANGE ITS CONTENTS.)***


## 3. Alignment
Ot2Rec uses the program IMOD for aligning raw images. To run IMOD, the appropriate module must be loaded using the command:
```
module load imod
```

### Creating configuration file
To create the configuration file for alignment in IMOD, run the following command:
```
o2r.align.new demo
```
which should produce the file `demo_align.yaml`, whose contents are listed below:
```
System:
    process_list: []
    output_path: ./stacks/
    output_rootname: TS
    output_suffix: ''
BatchRunTomo:
    setup:
        use_rawtlt: true
        pixel_size: 0.163
        rot_angle: 86.0
        gold_size: 0.0
        adoc_template: /opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc
        stack_bin_factor: 8
    preprocessing:
        delete_old_files: false
        remove_xrays: true
    coarse_align:
        bin_factor: 8
    patch_track:
        size_of_patches:
        - 300
        - 200
        num_of_patches:
        - 12
        - 8
        num_iterations: 4
        limits_on_shift:
        - 2
        - 2
        adjust_tilt_angles: true
    fine_align:
        num_surfaces: 1
        mag_option: fixed
        tilt_option: fixed
        rot_option: group
        beam_tilt_option: fixed
        use_robust_fitting: true
        weight_all_contours: true
```

### List of Parameters
Parameters | Descriptions 
 --- | --- 
**`System.process_list`** | (See above)
**`System.output_path`** | (See above)
**`System.output_rootname`** | Same as the prefix in previous steps. Should be automatically determined from previous metadata.
**`System.output_suffix`** | Extra information attached as suffix to output filenames.
 --- | ---
**`BatchRunTomo.setup.use_rawtlt`** | If set to `true`, IMOD will use the `.rawtlt` file generated from stack creation to determine image tilt angles, rather than directly from filenames.
**`BatchRunTomo.setup.pixel_size`** | Pixel size (in _nm_) of the motion-corrected images.
**`BatchRunTomo.setup.rot_angle`** | Rotational angle of electron beam. Can be obtained from MDOC files.
**`BatchRunTomo.setup.gold_size`** | Size (in nm) of gold fiducial particles. Set to `0` if fiducial-less.
**`BatchRunTomo.setup.adoc_template`** | Path to template file of BatchRunTomo directives.
**`BatchRunTomo.setup.stack_bin_factor`** | Raw image stacks downsampling factor
**`BatchRunTomo.preprocessing.delete_old_files`** | If set to `true`, remove original stack when excluding views
**`BatchRunTomo.preprocessing.remove_xrays`** | If set to `true`, IMOD will attempt to remove X-rays and other artefacts.
**`BatchRunTomo.coarse_align.bin_factor`** | Coarse aligned stack binning
**`BatchRunTomo.patch_track.size_of_patches`** | Size (in pixels) in X and Y of patches to track
**`BatchRunTomo.patch_track.num_of_patches`** | Number of patches to track in X and Y
**`BatchRunTomo.patch_track.num_iterations`** | Number of iterations (max. 4)
**`BatchRunTomo.patch_track.limits_on_shift`** | Maximum extent (in pixels) to which patches are allowed to move during alignment
**`BatchRunTomo.patch_track.adjust_tilt_angles`** | If set to `true`, IMOD will rerun patch-tracking procedure with tilt-angle offset.
**`BatchRunTomo.fine_align.num_surfaces`** | Number of surface(s) for angle analysis <br>(options: 1 \| 2)
**`BatchRunTomo.fine_align.mag_option`** | Type of magnification solution <br>(options: all \| group \| fix)
**`BatchRunTomo.fine_align.tilt_option`** | Type of tilt-angle solution <br>(options: all \| group \| fix)
**`BatchRunTomo.fine_align.rot_option`** | Type of rotation solution <br>(options: all \| group \| one \| fix)
**`BatchRunTomo.fine_align.beam_tilt_option`** | Type of beam-tilt solution <br>(options: fix \| search)
**`BatchRunTomo.fine_align.use_robust_fitting`** | If set to `true`, IMOD will use robust fitting to downsample some points.
**`BatchRunTomo.fine_align.weight_all_contours`** | If set to `true`, IMOD will apply weighting to entire contours from patch tracking.

***(Warning: Parameters under `BatchRunTomo.patch_track` and `BatchRunTomo.fine_align` sub-blocks affect alignment quality heavily. Default values are recommended for parameters under `BatchRunTomo.fine_align` sub-block.)***


### Running IMOD alignment
With the configuration file `demo_align.yaml` created, we can run IMOD by using the the command
```
o2r.align.run demo
```

At the end of the process, there should be a new metafile `demo_align_md.yaml`. <br>***(WARNING: This file will be used in later processing stages. DO NOT MANUALLY CHANGE ITS CONTENTS.)***

### Alignment of motion-corrected stacks created from other sources
Ot2Rec supports alignment of image stacks created from other sources (i.e. not using the Ot2Rec pipeline). The following command should be run
```
o2r.align.new_ext demo
```

The user will be asked several questions which help Ot2Rec to configure the input parameters automatically. This is essential as those parameters cannot be determined from metadata from previous steps. The output configuration file `demo_align.yaml` will have the same aforementioned format and the same parameters.

To start the alignment process, the user should use this command instead
```
o2r.align.run_ext demo
```


## 4. Reconstruction
The final step of image processing is reconstruction, which is a continuation from the alignment process in IMOD.

### Creating configuration file
To create the configuration file for reconstruction in IMOD, run the following command:
```
o2r.recon.new demo
```
which should produce the file `demo_recon.yaml`, whose contents are listed below:
```System:
    process_list: []
    output_path: ./stacks/
    output_rootname: TS
    output_suffix: ''
BatchRunTomo:
    setup:
        use_rawtlt: true
        pixel_size: 0.163
        rot_angle: 86.0
        gold_size: 0.0
        adoc_template: /opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc
    positioning:
        do_positioning: false
        unbinned_thickness: 3600
    aligned_stack:
        correct_ctf: false
        erase_gold: false
        2d_filtering: false
        bin_factor: 8
    reconstruction:
        thickness: 3600
    postprocessing:
        run_trimvol: true
        trimvol_reorient: rotate
```

### List of parameters
Parameters | Descriptions 
 --- | --- 
**`System.process_list`** | (See above)
**`System.output_path`** | (See above)
**`System.output_rootname`** | (See above)
**`System.output_suffix`** | (See above)
 --- | ---
**`BatchRunTomo.setup.use_rawtlt`** | (See above)
**`BatchRunTomo.setup.pixel_size`** | (See above)
**`BatchRunTomo.setup.rot_angle`** | (See above)
**`BatchRunTomo.setup.gold_size`** | (See above)
**`BatchRunTomo.setup.adoc_template`** | (See above)
**`BatchRunTomo.positioning.do_positioning`** | If set to `true`, IMOD will perform positioning for the stack.
**`BatchRunTomo.positioning.unbinned_thickness`** | Unbinned thickness (in pixels) for samples or whole tomogram
**`BatchRunTomo.aligned_stack.correct_ctf`** | If set to `true`, IMOD will attempt to correct CTF for the aligned stack.
**`BatchRunTomo.aligned_stack.erase_gold`** | If set to `true`, IMOD will attempt to erase gold fiducials.
**`BatchRunTomo.aligned_stack.2d_filtering`** | If set to `true`, IMOD will perform 2D filtering.
**`BatchRunTomo.aligned_stack.bin_factor`** | Binning to be applied on aligned stacks
**`BatchRunTomo.reconstruction.thickness`** | Thickness (in pixels) for reconstruction
**`BatchRunTomo.postprocessing.run_trimvol`** | If set to `true`, IMOD will run Trimvol on reconstruction
**`BatchRunTomo.postprocessing.trimvol_reorient`** | Reorientation in Trimvol <br>(options: none \| flip \| rotate)

### Running IMOD reconstruction
To start the reconstruction process, the user should use this command
```
o2r.recon.run demo
```