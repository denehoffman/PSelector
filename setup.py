from setuptools import setup, find_packages
import os

setup(
  name="pselector",
  version="0.0.1",
  author="Nathaniel Dene Hoffman",
  author_email="dene@cmu.edu",
  packages=find_packages("src"),
  package_dir={"": "src"},
  scripts=[],
  install_requires=[],
  zip_safe=False
)
