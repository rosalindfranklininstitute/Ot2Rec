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


import re
import os
from glob import glob1
from functools import partial
import multiprocessing as mp

import pandas as pd
import numpy as np
import scipy.constants as spk
from scipy.signal import convolve2d as c2d
import skimage.transform as skt
from skimage.transform import iradon, iradon_sart
from tqdm import tqdm
import mrcfile


from icecream import ic

from . import user_args as uaMod
from . import magicgui as mgMod
from . import metadata as mdMod
from . import logger as logMod


def get_psf(ctffile, point_source_recip, k2_grid, alpha_g):
    """
    Method to calculate PSF from CTFFIND4 outputs
    """
    with open(ctffile, 'r') as f:
        lines = f.readlines()

    # Get system configs
    get_pixel = re.compile('^# Pixel')
    pixel_line = list(filter(get_pixel.match, lines))[0]
    w2 = float(pixel_line.split(';')[3].split()[2])
    cs = float(pixel_line.split(';')[2].split()[2]) * 1e-3
    voltage = float(pixel_line.split(';')[1].split()[2]) * 1e3

    get_def = re.compile('^[^#]')
    def_line = list(filter(get_def.match, lines))[0]
    df1 = float(def_line.split()[1]) * 1e-10
    df2 = float(def_line.split()[2]) * 1e-10
    alpha_ast = np.deg2rad(float(def_line.split()[3]))
    dphi = float(def_line.split()[4])

    # Calculate defocus df
    ddf = df1 - df2
    df = 0.5 * (df1 + df2 + ddf * np.cos(2 * (alpha_g - alpha_ast)))

    # Calculate beam wavelength
    hc = spk.h * spk.c
    denom = np.sqrt(voltage * spk.e * (2 * spk.m_e * spk.c**2 + voltage * spk.e))
    wvl = hc / denom

    # Calculate phase shift chi
    chi = np.pi * wvl * k2_grid * (df - 0.5 * wvl**2 * k2_grid * cs) + \
        (dphi + np.arctan2(w2, np.sqrt(1 - w2**2)))

    # Calculate CTF
    ctf = np.exp(-1j*chi)

    # Calculate first-zero of CTF
    denom0 = wvl * (cs/wvl)**0.25
    df_min = np.min(df) / np.sqrt(cs*wvl)
    df_max = np.max(df) / np.sqrt(cs*wvl)
    q_min = np.sqrt(-df_min + np.sqrt(df_min**2+2)) / denom0
    q_max = np.sqrt(-df_max + np.sqrt(df_max**2+2)) / denom0

    # FT point-source and convolve with CTF
    ps_ctf_k = point_source_recip * ctf

    return 1/q_min, 1/q_max, np.absolute(np.fft.ifft2(ps_ctf_k))


def calculate_k_grids(image_size, pixel_size):
    """
    Method to calculate alpha_g (angle between g vector and horizontal axis) and norm2 on reciprocal grid

    Args:
        image_size (list): size of original image
        pixel_size (float): pixel size of original image

    Returns:
        ndarray, ndarray
    """

    # Create k-space coordinate grid
    kx_gridpts = np.fft.fftfreq(image_size[0], d=pixel_size)
    ky_gridpts = np.fft.fftfreq(image_size[1], d=pixel_size)

    kxv, kyv = np.meshgrid(kx_gridpts, ky_gridpts, indexing='ij', sparse=True)
    k2_grid = kxv**2 + kyv**2

    alpha_g = np.angle(kxv + 1j*kyv)

    return k2_grid, alpha_g


def reconstruct_slice(args, slice_idx):
    stack, angle_list = args
    sino_slice = stack[..., slice_idx]
    return iradon(sino_slice.T, angle_list)


def reconstruct_full_stack(stack, angle_list):
    pool = mp.Pool(mp.cpu_count())
    p = partial(reconstruct_slice, (stack, angle_list))
    tomo_map = pool.map(p, range(stack.shape[2]))
    tomo = np.array(tomo_map, dtype=np.float32)

    return tomo


def normalise_stack(tomo, pixel_size):
    image_size = tomo.shape

    # Create k-space coordinate grid
    kx_gridpts = np.fft.fftfreq(image_size[0], d=pixel_size)
    ky_gridpts = np.fft.fftfreq(image_size[1], d=pixel_size)
    kz_gridpts = np.fft.fftfreq(image_size[2], d=pixel_size)

    # Fourier transform PSF stack
    ctf_stack = np.fft.fftn(tomo)

    # Normalise CTF stack and back FFT
    zero_freq = np.array([np.argmin(np.abs(kx_gridpts)),
                          np.argmin(np.abs(ky_gridpts)),
                          np.argmin(np.abs(kz_gridpts))])
    ctf_stack_norm = ctf_stack / ctf_stack[zero_freq[0], zero_freq[1], zero_freq[2]]
    psf_out = np.absolute(np.fft.ifftn(ctf_stack_norm))
    psf_out /= np.max(psf_out)

    return psf_out


def run():
    """
    Method to run simulator for CTF from CTFFIND4 outputs
    """
    logger = logMod.Logger(log_path="o2r_ctfsim.log")

    # Parse user inputs
    args = mgMod.get_args_ctfsim.show(run=True)

    project_name = args.project_name.value
    rootname = project_name
    if args.rootname.value != "":
        while args.rootname.value.endswith('/'):
            rootname = args.rootname.value[:-1]

    pixel_size = args.pixel_res.value * 1e-10
    ds_factor = args.ds_factor.value

    # Read in metadata from ctffind
    ctffind_md_file = project_name + '_ctffind_mdout.yaml'
    if not os.path.isfile(ctffind_md_file):
        logger(level="error",
               message="CTFFind metadata not found.")
        raise IOError("Error in Ot2Rec.ctfsim.run: ctffind metadata not found.")

    ctffind_obj = mdMod.read_md_yaml(project_name=project_name,
                                     job_type='ctfsim',
                                     filename=ctffind_md_file)
    ctffind_md = pd.DataFrame(ctffind_obj.metadata)

    # Read image to get dimensions
    sample_image = ctffind_md.iloc[0].file_paths
    with mrcfile.open(sample_image) as source:
        source_dim = skt.downscale_local_mean(source.data, (ds_factor, ds_factor)).shape

    # Generate point source
    ps = np.zeros(source_dim[-2:], dtype=np.float32)
    ps[ps.shape[0] // 2, ps.shape[1] // 2] = 1
    ps_k = np.fft.fft2(ps).astype(np.cdouble)

    # Calculate the grids in reciprocal space
    k2_grid, alpha_g_grid = calculate_k_grids(source_dim, pixel_size * ds_factor)

    # Grab tilt series numbers and tilt angles from metadata
    ts_list = sorted(pd.Series(ctffind_md['ts']).unique())

    logger(level="info",
           message="Ot2Rec-CTFSim started.")

    tqdm_iter = tqdm(ts_list, ncols=100)
    for curr_ts in tqdm_iter:
        # Create folders and subfolders
        subfolder_path = f'{args.output_folder.value}/{rootname}_{curr_ts:04}'
        os.makedirs(subfolder_path, exist_ok=True)

        # Find txt files from ctffind
        glob_list = glob1('./ctffind/', f'{rootname}_{curr_ts:04}_*ctffind.txt')

        angle_list = [float(i.split('/')[-1].split('_')[2]) for i in glob_list]
        angle_index = [sorted(angle_list).index(i) for i in angle_list]

        full_ctf = np.empty(shape=(len(angle_list), *source_dim[-2:]),
                            dtype=np.float32)
        mean_res = np.empty(shape=(len(angle_list)),
                            dtype=np.float32)

        for index in range(len(angle_index)):
            res0, res1, full_ctf[angle_index[index], ...] = get_psf(ctffile='./ctffind/' + glob_list[index],
                                                                    point_source_recip=ps_k,
                                                                    k2_grid=k2_grid,
                                                                    alpha_g=alpha_g_grid)
            mean_res[index] = 0.5*(res0+res1) * 1e10

        # calculate PSF
        (xmin, ymin, zmin) = (
            (source_dim[0] - args.dims.value[0]) // 2,
            (source_dim[0] - args.dims.value[1]) // 2,
            (source_dim[1] - args.dims.value[2]) // 2,
        )
        (xmax, ymax, zmax) = (xmin + args.dims.value[0], ymin + args.dims.value[1], zmin + args.dims.value[2])
        psf_unnorm = reconstruct_full_stack(full_ctf, sorted(angle_list))[xmin:xmax, ymin:ymax, zmin:zmax]

        full_psf = normalise_stack(psf_unnorm, pixel_size*ds_factor)

        # Write out psf stack
        with mrcfile.new(subfolder_path + f'/{rootname}_{curr_ts:04}_PSF.mrc', overwrite=True) as f:
            f.set_data(np.asarray(full_psf, dtype=np.float32))

        # Write out rawtlt file
        with open(subfolder_path + f'/{rootname}_{curr_ts:04}.tlt', 'w') as f:
            for angle in sorted(angle_list):
                f.writelines(str(angle) + '\n')

        # Write out resolution file
        with open(subfolder_path + f'/{rootname}_{curr_ts:04}.res', 'w') as f:
            np.savetxt(f, X=mean_res)
