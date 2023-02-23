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


from setuptools import setup, find_packages


setup(
    version='0.3.2',
    name='Ot2Rec',
    description='Ot2Rec',
    url='https://github.com/rosalindfranklininstitute/Ot2Rec',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    test_suite='tests',
    license='Apache License, Version 2.0',
    zip_safe=False,
    install_requires=[
        'tqdm',
        'pandas',
        'pyyaml',
        'multiprocess',
        'icecream',
        'beautifultable',
        'scikit-image',
        'mrcfile',
        'tifffile',
        'redlionfish',
        'magicgui',
        'pyqt5',
        # 'mdocfile',
        'joblib'
    ],
    entry_points={
        "console_scripts": [
            "o2r.new=Ot2Rec.main:new_proj",

            "o2r.mc.new=Ot2Rec.motioncorr:create_yaml",
            "o2r.mc.run=Ot2Rec.motioncorr:run",

            "o2r.excludebadtilts.new=Ot2Rec.exclude_bad_tilts:create_yaml",
            "o2r.excludebadtilts.run=Ot2Rec.exclude_bad_tilts:run",
            "o2r.recombinebadtilts=Ot2Rec.exclude_bad_tilts:recombine_bad_tilts",

            "o2r.ctffind.new=Ot2Rec.ctffind:create_yaml",
            "o2r.ctffind.run=Ot2Rec.ctffind:run",

            "o2r.ctfsim.run=Ot2Rec.ctfsim:run",

            "o2r.imod.align.new=Ot2Rec.align:create_yaml",
            "o2r.imod.align.stacks=Ot2Rec.align:imod_create_stacks",
            "o2r.imod.align.run=Ot2Rec.align:imod_standard_align",

            "o2r.imod.align.new_ext=Ot2Rec.align:create_yaml_stacked",
            "o2r.imod.align.run_ext=Ot2Rec.align:imod_align_ext",

            "o2r.imod.align.stats=Ot2Rec.align:get_align_stats",

            "o2r.imod.recon.new=Ot2Rec.recon:create_yaml",
            "o2r.imod.recon.run=Ot2Rec.recon:run",

            "o2r.savu.recon.new=Ot2Rec.savurecon:create_yaml",
            "o2r.savu.recon.run=Ot2Rec.savurecon:run",

            "o2r.aretomo.new=Ot2Rec.aretomo:create_yaml",
            "o2r.aretomo.run=Ot2Rec.aretomo:run",

            "o2r.deconv.run=Ot2Rec.rlf_deconv:run",

            "o2r.cleanup=Ot2Rec.main:cleanup",

            "o2r.runall.imod=Ot2Rec.main:run_all_imod",
        ]
    }
)
