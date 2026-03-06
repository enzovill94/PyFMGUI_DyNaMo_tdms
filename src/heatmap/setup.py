#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for PSNEX Map Analysis GUI
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="psnex-map-analysis",
    version="0.1.0",
    author="Lorenzo Villanueva",
    author_email="lorenzo.villanueva@inserm.fr",
    description="PSNEX Map Analysis GUI for heatmap visualization and ROI analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DyNaMo-INSERM/PyFMGUI_DyNaMo",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Visualization",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "psnex-map-analysis=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
