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


from pathlib import Path
from magicgui import magicgui as mg
import yaml

from . import logger as logMod
from . import params as prmMod
from . import metadata as mdMod


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",

    project_name={"label": "Project name *"},
    source_folder={"widget_type": "FileEdit",
                   "label": "Source folder *",
                   "mode": "d"},
    mdocs_folder={"widget_type": "FileEdit",
                 "label": "MDOCs folder (overridden if 'No MDOCs'==True) *",
                 "mode": "d"},
    folder_prefix={"label": "Folder prefix (if tilt series in subfolders)"},
    file_prefix={"label": "File prefix (if different from project name)"},
    ext={"widget_type": "ComboBox",
         "label": "Image file extension",
         "choices": ["mrc", "tif", "eer"]},
    stack_field={"min": 0,
                 "label": "Stack index field #"},
    index_field={"min": 0,
                 "label": "Image index field #"},
    tiltangle_field={"min": 0,
                     "label": "Tilt angle field #"},
    no_mdoc={"label": "No MDOCs"},
    return_only={"label": "Only return parameters without file creation (not recommended)"}
)
def get_args_new_proj(
        project_name="",
        source_folder=Path("../raw/"),
        mdocs_folder=Path("../raw/"),
        folder_prefix="",
        file_prefix="",
        ext="mrc",
        stack_field=0,
        index_field=1,
        tiltangle_field=2,
        no_mdoc=False,
        *,
        return_only=False,
):
    """
    Function to add arguments to parser for new project

    ARGS:
    project_name (str)    :: Name of current project
    source_folder (str)   :: Path to folder with raw images (Default: ../raw/)
    folder_prefix (str)   :: Common prefix of raw tilt series folder(s)
    file_prefix (str)     :: Common prefix of raw image files (Default: project)
    ext (str)             :: Extension of raw image files (Default: mrc)
    stack_field (int)     :: Field number of tilt series indices (Default: 0)
    index_field (int)     :: Field number of image indices (Default: 1)
    tiltangle_field (int) :: Field number of tilt angles (Default: 2)
    no_mdoc (bool)        :: True if no MDOC file provided (Default: False)
    mdoc_folder (str)     :: Path to folder with raw images (Default: ../raw/)

    OUTPUTs:
    Namespace
    """
    logger = logMod.Logger(log_path="new_proj.log")
    args = asObject(locals())

    if return_only:
        return locals()

    prmMod.new_master_yaml(args)

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=args.project_name,
                          job_type='master')

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()
    if not args.no_mdoc:
        meta.get_mc2_temp()
        meta.get_acquisition_settings()

    master_md_name = args.project_name + '_master_md.yaml'
    acqui_md_name =  args.project_name + '_acquisition_md.yaml'
    with open(master_md_name, 'w') as f:
        yaml.dump(meta.metadata, f, indent=4)
    with open(acqui_md_name, 'w') as g:
        yaml.dump(meta.acquisition, g, indent=4)

    logger(level="info",
           message="Master metadata file created.")

    return locals()
