from setuptools import setup, find_packages
from pathlib import Path
SRC = Path(__file__).parent / "src/pselector"
setup(
    name="pselector",
    version="0.0.2",
    author="Nathaniel Dene Hoffman",
    author_email="dene@cmu.edu",
    packages=find_packages("src"),
    package_dir={"": "src"},
    scripts=[str(SRC / "MakePSelector")],
    install_requires=["particle", 'tomli; python_version < "3.11"'],
    zip_safe=False
)
