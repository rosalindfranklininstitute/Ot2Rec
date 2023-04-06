# Copyright 2023 Rosalind Franklin Institute
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

import glob
import os
import re
from pathlib import Path

import mdocfile as mdf
import yaml
from mdocfile.mdoc import Mdoc

from magicgui import magicgui
from Ot2Rec import logger as logMod


def reassign_names_from_mdoc(mdocs: list) -> dict:
    """Genenerate new filenames for the micrographs based on mdocs
    New filenaming convention is
    <project name>_<tomogram number>_<tilt number>_<tilt angle>.<ext>
    Each unique mdoc receives a new tomogram number, e.g.,
        TS_01.mdoc -> tomogram number 001
        TS_01_02.mdoc -> tomogram number 002
        TS_abc.mdoc -> tomogram number 003

    Args:
        mdocs (list): List of paths to the mdocs

    Returns:
        dict: Maps original filenames to new filenames
    """
    reassigned_names = {}
    ts_index = 1

    for mdoc in mdocs:
        df = mdf.read(mdoc)

        for micrograph in range(len(df)):
            tilt_index = df.iloc[micrograph].ZValue + 1
            tilt_angle = df.iloc[micrograph].TiltAngle
            micrograph_fname = re.split(r"/|\\", str(df.iloc[micrograph].SubFramePath))[
                -1
            ]
            proj_name = micrograph_fname.split("_")[0]
            extension = os.path.splitext(micrograph_fname)[-1]
            new_micrograph_fname = f"{proj_name}_{ts_index:03}_{tilt_index:03}_{int(tilt_angle):.2f}{extension}"
            reassigned_names[micrograph_fname] = new_micrograph_fname

        ts_index += 1

    return reassigned_names


def rename_files(directory: Path, reassigned_names: dict):
    """Renames files in `directory` according to their new filenames defined in
     `reassigned_names`

    Args:
        directory (Path): Directory where the files to be renamed are stored
        reassigned_names (dict): Mapping of original filenames to new filenames
    """
    for src, dst in list(reassigned_names.items()):
        os.rename(src=os.path.join(directory, src), dst=os.path.join(directory, dst))


def update_mdocs(
    mdocs: list,
    new_mdocs_directory: Path,
    micrograph_directory: Path,
    reassigned_names: dict,
):
    """Create new mdocs with new filenames

    Updates the SubFramePath of each tilt in the mdoc with the new filename and
     saves this updated mdoc with the updated name.

    For example,
    Mdoc filename:
    TS_01_02.mdoc -> TS_001.mdoc

    Micrograph name in SubFramePath:
    TS_01_02_001_0.00_EER.eer -> TS_001_001_0.00.eer


    Args:
        mdocs (list): List of paths to mdocs
        new_mdocs_directory (Path): Directory to save new updated mdocs
        micrograph_directory (Path): Directory where raw micrographs are. Used
            to write absolute paths in the new mdocs
        reassigned_names (dict): Mapping of old filenames to new filenames
    """
    if os.path.isdir(new_mdocs_directory) is False:
        Path(new_mdocs_directory).mkdir(exist_ok=True)
    for mdoc in mdocs:
        mdoc_obj = Mdoc.from_file(mdoc)

        for micrograph in mdoc_obj.section_data:
            original_name = re.split(r"/|\\", str(micrograph.SubFramePath))[-1]
            micrograph.SubFramePath = str(
                f"{micrograph_directory}/{reassigned_names[original_name]}"
            )

        last_micrograph_split = reassigned_names[original_name].split("_")
        proj_name = last_micrograph_split[0]
        ts_index = last_micrograph_split[1]
        new_mdoc = f"{proj_name}_{ts_index:03}.mdoc"

        with open(f"{new_mdocs_directory}/{new_mdoc}", "w") as f:
            f.write(mdoc_obj.to_string())


def write_md_out(reassigned_names: dict):
    """Write yaml file for mapping old to new filenames

    Args:
        reassigned_names (dict): Mapping of old filenames to new filenames
    """
    with open("./ot2rec_reassigned_names.yaml", "w") as f:
        yaml.dump(reassigned_names, f)


@magicgui(
    call_button="Rename files",
    layout="vertical",
    mdocs_directory={
        "widget_type": "FileEdit",
        "label": "Directory where mdocs are stored*",
        "mode": "d",
    },
    micrograph_directory={
        "widget_type": "FileEdit",
        "label": "Directory where raw micrographs are stored*",
        "mode": "d",
    },
    message={
        "widget_type": "Label",
        "label": """
        Renames micrographs and creates new mdocs based on the file naming convention
        <project_name>_<tomogram_number>_<tilt_number>_<tilt_angle>.<ext>
        where each unique mdoc gets its own tomogram number starting from 001.
    """,
    },
)
def rename_all(mdocs_directory: Path, micrograph_directory: Path, message: str = ""):
    """Renames microraphs and mdocs to an Ot2Rec-friendly filenaming pattern
    and save updated mdocs in a new directory `ot2rec_mdocs`.

    New filename format is
    <project name>_<tomogram number>_<tilt number>_<tilt angle>.<ext>
    Each unique mdoc receives a new tomogram number, e.g.,
        TS_01.mdoc -> tomogram number 001
        TS_01_02.mdoc -> tomogram number 002
        TS_abc.mdoc -> tomogram number 003

    Args:
        mdocs_directory (Path): Original directory containing mdocs
        micrograph_directory (Path): Directory containing raw micrographs
        message (str): Dummy variable required to print the help message
    """
    logger = logMod.Logger(log_path="./o2r_rename.log")
    logger(
        level="info",
        message=f"Renaming files in {micrograph_directory} according to mdocs in {mdocs_directory}",
    )

    mdocs_list = glob.glob(f"{mdocs_directory}/*mdoc")
    reassigned_names = reassign_names_from_mdoc(mdocs_list)
    rename_files(micrograph_directory, reassigned_names)
    logger(level="info", message=f"Renamed {len(reassigned_names)} files")

    update_mdocs(mdocs_list, "./ot2rec_mdocs", micrograph_directory, reassigned_names)
    logger(level="info", message="Updated mdocs now saved in ./ot2rec_mdocs")

    write_md_out(reassigned_names)
    logger(
        level="info",
        message="Mapping of old to new filenames available in ot2rec_reassigned_names.yaml",
    )
    logger(level="info", message="Renaming complete, you can close the GUI now")


def rename_all_with_mgui():
    """Collects user parameters and renames microraphs and mdocs to an
    Ot2Rec-friendly filenaming pattern and save updated mdocs in a new
    irectory `ot2rec_mdocs`.

    MagicGUI will collect `mdocs_directory` and `micrograph_directory`.

    New filename format is
    <project name>_<tomogram number>_<tilt number>_<tilt angle>.<ext>
    Each unique mdoc receives a new tomogram number, e.g.,
        TS_01.mdoc -> tomogram number 001
        TS_01_02.mdoc -> tomogram number 002
        TS_abc.mdoc -> tomogram number 003

    """
    rename_all.show(run=True)
