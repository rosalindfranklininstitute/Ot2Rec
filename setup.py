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
    version='1.0a',
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
        'redlionfish',
    ],
    entry_points={
        "console_scripts": [
            "o2r.new=Ot2Rec.main:new_proj",

            "o2r.mc.new=Ot2Rec.motioncorr:create_yaml",
            "o2r.mc.run=Ot2Rec.motioncorr:run",

            "o2r.ctffind.new=Ot2Rec.ctffind:create_yaml",
            "o2r.ctffind.run=Ot2Rec.ctffind:run",
            
            "o2r.ctfsim.run=Ot2Rec.ctfsim:run",

            "o2r.align.new=Ot2Rec.main:create_align_yaml",
            "o2r.align.stacks=Ot2Rec.main:create_stacks",
            "o2r.align.run=Ot2Rec.main:run_align",
            "o2r.align.stats=Ot2Rec.main:get_align_stats",

            "o2r.align.new_ext=Ot2Rec.main:create_align_yaml_stacked",
            "o2r.align.run_ext=Ot2Rec.main:run_align_ext",

            "o2r.recon.new=Ot2Rec.main:create_recon_yaml",
            "o2r.recon.run=Ot2Rec.main:run_recon",

            "o2r.savu.new=Ot2Rec.savurecon:create_yaml",
            "o2r.savu.run=Ot2Rec.savurecon:run",

            "o2r.deconv.run=Ot2Rec.main:run_rlf_deconv",

            "o2r.cleanup=Ot2Rec.main:cleanup",
            "o2r.runall=Ot2Rec.main:run_all",
        ]
    }
)
