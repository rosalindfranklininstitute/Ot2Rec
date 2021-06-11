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
            ]
        }
    )

if __name__ == '__main__':
    main()
