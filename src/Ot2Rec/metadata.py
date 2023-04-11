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


import os
import re
import itertools
from functools import partial
import multiprocessing as mp
import subprocess
from glob import glob
from tqdm import tqdm

from tifffile import TiffFile as tf
import xmltodict as x2d

import yaml
import mdocfile as mdf
import pandas as pd
from icecream import ic

from . import params as prmMod
from .prog_bar import *


class Metadata:
    """
    Class encapsulating Metadata objects
    """

    # First define conversion table between job (module) name and file suffixes
    suffix_dict = {
        "master": "proj",
        "motioncorr": "mc2",
        "ctffind": "ctffind",
        "align": "align",
        "reconstruct": "recon",
    }

    def __init__(
        self,
        project_name: str,
        job_type: str,
        md_in=None,
    ):
        """
        Initialise Metadata object

        Args:
            project_name: project name
            job_type: what job is being done
                (motioncorr/ctffind/align/reconstruct)
            md_in: dictionary read from yaml file containing existing metadata
        """

        self.project_name = project_name
        self.job_type = job_type
        self.metadata = md_in
        self.acquisition = dict()

        # Obtain parameters first
        if self.job_type in ["master", "motioncorr", "ctffind", "align", "reconstruct"]:
            self.get_param()

        # Define empty lists for later use
        (
            self.image_paths,
            self.mdocs_paths,
            self.tilt_series,
            self.image_idx,
            self.tilt_angles,
        ) = ([], [], [], [], [])

    def get_param(self):
        """
        Subroutine to get parameters for current job
        """

        param_file = (
            self.project_name + "_" + Metadata.suffix_dict[self.job_type] + ".yaml"
        )
        self.prmObj = prmMod.read_yaml(
            project_name=self.project_name, filename=param_file
        )
        self.params = self.prmObj.params

    def create_master_metadata(self):
        """
        Subroutine to create master metadata from raw data.
        Metadata include: image paths, tilt series indices, tilt angles
        """

        # Define criteria for searching subfolders (tilt series) within source folder
        if self.params["TS_folder_prefix"] == "*":
            ts_subfolder_criterion = "*"
        elif (
            self.params["TS_folder_prefix"] != "*"
            and len(self.params["TS_folder_prefix"]) > 0
        ):
            ts_subfolder_criterion = self.params["TS_folder_prefix"] + "_*"

        # Source folder should not end with forward slash so remove them
        while self.params["source_folder"].endswith("/"):
            self.params["source_folder"] = self.params["source_folder"][:-1]

        # Source folder should not end with forward slash so remove them
        while self.params["mdocs_folder"].endswith("/"):
            self.params["mdocs_folder"] = self.params["mdocs_folder"][:-1]

        # Find files and check
        if len(self.params["TS_folder_prefix"]) > 0:
            raw_images_list = glob(
                "{}/{}/{}_*.{}".format(
                    self.params["source_folder"],
                    ts_subfolder_criterion,
                    self.params["file_prefix"],
                    self.params["filetype"],
                )
            )
        else:
            raw_images_list = glob(
                "{}/{}_*.{}".format(
                    self.params["source_folder"],
                    self.params["file_prefix"],
                    self.params["filetype"],
                )
            )

        if len(raw_images_list) == 0:
            raise IOError(
                "Error in Ot2Rec.metadata.Metadata.create_master_metadata: "
                "No vaild files found using given criteria."
            )

        # Find MDOC files and check
        if self.params["mdocs_folder"] is None:
            self.mdocs_paths = glob(
                "{}/{}_*.mdoc".format(
                    self.params["source_folder"],
                    self.params["file_prefix"],
                )
            )
        else:
            self.mdocs_paths = glob(
                "{}/{}_*.mdoc".format(
                    self.params["mdocs_folder"],
                    self.params["file_prefix"],
                )
            )

        # Convert potentially relative file paths to absolute paths
        raw_images_list = sorted([os.path.abspath(image) for image in raw_images_list])
        self.mdocs_paths = sorted([os.path.abspath(mdoc) for mdoc in self.mdocs_paths])

        # Extract information from image file names
        for curr_image in raw_images_list:
            self.image_paths.append(curr_image)

            # Get length of filename prefix
            prefix_length = len(self.params["file_prefix"].split("_"))

            # Extract tilt series number
            split_path_name = curr_image.split("/")[-1].replace("[", "_").split("_")
            try:
                ts_index = "".join(
                    i
                    for i in split_path_name[
                        self.params["image_stack_field"] + prefix_length
                    ]
                )
            except (IndexError, ValueError):
                raise IndexError(
                    f"Error in Ot2Rec.metadata.Metadata.create_master_metadata. "
                    f"Failed to get tilt series number from file path {curr_image}."
                )
            self.tilt_series.append(str(ts_index))

            # Extract image index number
            try:
                idx = int(
                    "".join(
                        i
                        for i in split_path_name[
                            self.params["image_index_field"] + prefix_length
                        ]
                        if i.isdigit()
                    )
                )
            except (IndexError, ValueError):
                raise IndexError(
                    f"Error in Ot2Rec.metadata.Metadata.create_master_metadata. "
                    f"Failed to get tilt series number from file path {curr_image}."
                )
            self.image_idx.append(idx)

            # Extract tilt angle
            try:
                tilt_angle = float(
                    split_path_name[
                        self.params["image_tiltangle_field"] + prefix_length
                    ]
                    .replace(f".{self.params['filetype']}", "")
                    .replace("[", "")
                    .replace("]", "")
                )
            except (IndexError, ValueError):
                raise IndexError(
                    f"Error in Ot2Rec.metadata.Metadata.create_master_metadata. "
                    f"Failed to get tilt angle from file path {curr_image}."
                )
            self.tilt_angles.append(tilt_angle)

        # Save metadata as a dictionary --- easier to dump as yaml
        self.metadata = dict(
            file_paths=self.image_paths,
            ts=self.tilt_series,
            image_idx=[int(i) for i in self.image_idx],
            angles=self.tilt_angles,
        )

    def get_num_frames(self, file_path, target_nframes=15):
        if self.params['filetype'] == "eer":
            with tf(file_path) as f:
                tag = f.pages[0].tags['65001']
                data = tag.value.decode('UTF-8')

            parsed = x2d.parse(data)
            metadata = dict()
            for item in parsed["metadata"]["item"]:
                key = item["@name"]
                value = item["#text"]
                metadata[key] = value

                try:
                    unit = item["@unit"]
                    metadata[f"{key}.unit"] = unit
                except:
                    pass

            nframes = int(metadata["numberOfFrames"])
        else:
            command = ['header', file_path]
            text = subprocess.run(command, capture_output=True, check=True)
            text_split = str(text.stdout).split('\\n')
            r = re.compile(r'\s*Number')
            line = list(filter(r.match, text_split))[0].lstrip()

            nframes = int(re.split(r'\s+', line)[-1])

        sampling = max(1, nframes // target_nframes)

        return [nframes, sampling]


    @staticmethod
    def get_num_frames_parallel(func, filelist, target_nframes=15, np=8):
        """
        Args:
            func (func): function to be parallelised
            filelist (list): list of image files to be passed into the function
        """
        func_filelist = partial(func, target_nframes=target_nframes)
        with mp.Pool(np) as p:
            result = p.map(func_filelist, filelist)

        return result


    @staticmethod
    def get_ts_dose(mdoc_in, start=0):
        with open(mdoc_in, "r") as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]

        blocks = [
            list(y) for x, y in itertools.groupby(lines, lambda z: z == "") if not x
        ]
        ts_all_info = [block for block in blocks if block[0].startswith(r"[ZValue")]

        ts_dose_dict = {}
        for frame_idx in range(len(ts_all_info)):
            file_idx = frame_idx + start

            image = ts_all_info[frame_idx]
            image_split = [re.split(r"\s*=\s*", line) for line in image]
            image_split_t = list(map(list, zip(*image_split)))
            image_dict = dict(zip(image_split_t[0], image_split_t[1]))

            ts_dose_dict[file_idx] = float(image_dict["ExposureDose"])

        return ts_dose_dict


    def get_mc2_temp(self):
        df = pd.DataFrame(self.metadata)

        if self.params["mdocs_folder"] is None:
            base_folder = "/".join(df.file_paths.values[0].split("/")[:-1])
        else:
            base_folder = "/".join(self.mdocs_paths[0].split("/")[:-1])

        df["num_frames"] = None
        df["ds_factor"] = None
        df["frame_dose"] = None

        with prog_bar as p:
            clear_tasks(p)
            for curr_ts in p.track(list(set(df.ts))):
                mdoc_path = (
                    f"{base_folder}/{self.params['file_prefix']}_" + str(curr_ts) + ".mdoc"
                )
                mdoc = mdf.read(mdoc_path)
                ts_dose_dict = self.get_ts_dose(mdoc_path, 1)

                ts_image_list = df[df["ts"] == curr_ts]["file_paths"].to_list()
                ts_image_idx_list = df[df["ts"] == curr_ts]["image_idx"].to_list()
                ts_num_frame_list = self.get_num_frames_parallel(
                    func=self.get_num_frames,
                    filelist=ts_image_list,
                )

                for curr_idx in ts_image_idx_list:
                    nf, dsf = ts_num_frame_list[curr_idx - 1]
                    df.loc[
                        (df.ts == curr_ts) & (df.image_idx == curr_idx), "num_frames"
                    ] = nf
                    df.loc[
                        (df.ts == curr_ts) & (df.image_idx == curr_idx), "ds_factor"
                    ] = dsf
                    df.loc[
                        (df.ts == curr_ts) & (df.image_idx == curr_idx), "frame_dose"
                    ] = (ts_dose_dict[curr_idx] / nf)

            self.metadata["num_frames"] = df.num_frames.to_list()
            self.metadata["ds_factor"] = df.ds_factor.to_list()
            self.metadata["frame_dose"] = df.frame_dose.to_list()


    def get_acquisition_settings(self):
        df = pd.DataFrame(self.metadata)
        if self.params["mdocs_folder"] is None:
            base_folder = "/".join(df.file_paths.values[0].split("/")[:-1])
        else:
            base_folder = "/".join(self.mdocs_paths[0].split("/")[:-1])

        ts = list(set(df.ts))[0]  # Assuming settings same across one data set
        mdoc_path = f"{base_folder}/{self.params['file_prefix']}_" + str(ts) + ".mdoc"
        mdoc = mdf.read(mdoc_path)

        self.acquisition["magnification"] = int(mdoc.Magnification.unique()[0])
        self.acquisition["pixel_spacing"] = float(mdoc.PixelSpacing.unique()[0])
        self.acquisition["spot_size"] = float(mdoc.SpotSize.unique()[0])
        self.acquisition["rotation_angle"] = float(mdoc.RotationAngle.unique()[0])
        self.acquisition["voltage"] = float(mdoc.Voltage.unique()[0])
        self.acquisition["image_size"] = list(mdoc.ImageSize.unique()[0])


def read_md_yaml(
    project_name: str,
    job_type: str,
    filename: str,
):
    """
    Function to read in YAML file containing metadata

    Args:
        project_name: Name of current project
        job_type: what job is being done (motioncorr/ctffind/align/reconstruct)
        filename: Name of the YAML file to be read

    Returns:
        ot2rec.metadata.Metadata
    """

    # Check if file exists
    if not os.path.isfile(filename):
        raise IOError("Error in Ot2Rec.metadata.read_md_yaml: File not found.")

    with open(filename, "r") as f:
        md = yaml.load(f, Loader=yaml.FullLoader)

    return Metadata(project_name=project_name, job_type=job_type, md_in=md)
