from setuptools import setup, find_packages
from pathlib import Path
SRC = Path(__file__).parent / "src/pselector"
setup(
    name="pselector",
    version="0.0.1",
    author="Nathaniel Dene Hoffman",
    author_email="dene@cmu.edu",
    packages=find_packages("src"),
    package_dir={"": "src"},
    scripts=[str(SRC / "MakePSelector")],
    install_requires=["particle"],
    zip_safe=False
)
