from setuptools import setup, find_packages
from pathlib import Path
SRC = Path(__file__).parent / "src/pselector"
setup(
    name="pselector",
    version="1.1.0",
    author="Nathaniel Dene Hoffman",
    author_email="dene@cmu.edu",
    maintainer="Nathaniel Dene Hoffman",
    maintainer_email="dene@cmu.edu",
    url="https://github.com/denehoffman/PSelector",
    description="A tool to generate GlueX analysis DSelector code from a TOML config",
    long_description="""
    MakePSelector parses a TOML configuration file and generates C code for GlueX's
    DSelector, a modification of the ROOT TSelector class. Within the configuration
    file, a user can define
    * Four-vectors and boosted reference frames
    * Histograms
    * Cuts
    * Weights
    * Flat tree output branches
    * Uniqueness tracking
    Additionally, users can use the uniqueness tracking interface to generate
    histograms of events which pass a subset of selections. Users can also insert
    raw C code into the appropriate location in the DSelector.

    The intent of this project is to make the writing of this analysis tool painless.
    In C, creating a new histogram requires the user to type the variable name
    *correctly* in three different places, once in the header, once when they
    initialize it, and once when they fill it. Additionally, if a user wants to reuse
    histogram parameters or create 2D histograms which mirror existing 1D histogram
    pairs, they must write nearly identical code in each of these three places again.
    MakePSelector was designed to avoid this problem, along with several others.
    Another example is the confusing syntax of uniquness tracking, which is simplified
    in MakePSelector, as well as the process for writing output trees and flat trees.
    """,
    license="License :: OSI Approved :: MIT License",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: C",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: Physics",
        ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    scripts=[str(SRC / "MakePSelector")],
    install_requires=["particle", 'tomli; python_version < "3.11"'],
    zip_safe=False
)
