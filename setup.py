"""
Copyright (C) 2021 Rosalind Franklin Institute

This code is distributed under the ApacheV2 license
"""
from skbuild import setup

def main():
    """
    Setup the package
    """

    setup(
        package_dir={"": "src"},
        packages=["Ot2Rec"],
        install_requires=[],
        entry_points={
            "console_scripts": [
                "o2r.new=Ot2Rec.main:new_proj",
                "o2r.get_master=Ot2Rec.main:get_master_metadata",
                "o2r.mc.new=Ot2Rec.main:create_mc2_yaml",
                "o2r.mc.run=Ot2Rec.main:run_mc2",
                "o2r.ctffind.new=Ot2Rec.main:create_ctffind_yaml",
                "o2r.ctffind.run=Ot2Rec.main:run_ctffind",
                "o2r.align.new=Ot2Rec.main:create_align_yaml",
            ]
        }
    )

if __name__ == '__main__':
    main()
