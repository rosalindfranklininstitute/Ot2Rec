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
import numpy as np
import scipy.constants as spk


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
    df = 0.5 * (df1 + df2 + ddf*np.cos(2*(alpha_g-alpha_ast)))

    # Calculate beam wavelength
    hc = spk.h * spk.c
    denom = np.sqrt(voltage * spk.e * (2*spk.m_e*spk.c**2 + voltage * spk.e))
    wvl = hc / denom

    # Calculate phase shift chi
    chi = np.pi * wvl * k2_grid * (df - 0.5*wvl**2*k2_grid*cs) + \
        (dphi + np.arctan2(w2, np.sqrt(1-w2**2)))

    # Calculate CTF
    ctf = -np.sin(chi, dtype=np.float32)

    # FT point-source and convolve with CTF
    ps_ctf_k = point_source_recip * ctf
    psf = np.real(np.fft.ifft2(ps_ctf_k)).astype(np.float32)

    return psf


def calculate_k_grids(image_size, pixel_size):
    """
    Method to calculate alpha_g (angle between g vector and horizontal axis) and norm2 on reciprocal grid

    ARGS:
    image_size (list) :: size of original image
    pixel_size (float) :: pixel size of original image

    OUTPUTS:
    ndarray, ndarray
    """

    # Create k-space coordinate grid
    kx_gridpts = np.fft.fftfreq(image_size[0], d=pixel_size)
    ky_gridpts = np.fft.fftfreq(image_size[1], d=pixel_size)

    kxv, kyv = np.meshgrid(kx_gridpts, ky_gridpts, indexing='ij')
    k2_grid = kxv**2 + kyv**2

    alpha_g = np.arctan2(kxv, kyv, dtype=np.float32)

    return k2_grid, alpha_g
