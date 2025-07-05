# Atomic Force Microscopy (AFM) based Force Spectroscopy (FS) data analysis software 

This software is a automated, flexible, easy to use, user-friendly package that facilitates 
the data analysis of force curves obtained from AFM based FS experiments.


The software package is capable to handle files obtained from experiments using a home-built HS-AFM instruments in addition to conventional AFM files obtained from experiments using JPK instruments. The package will be extended to handle other file formats such as files from Asylum research, NT-MDT spectrum instruments and Bruker instruments. This adaptation will allow the package to have more portability and will facilitate the analysis for a wide range of users.

## Installation

Before installing the software package make sur you have Python 3.8 .

The easiest way to install Python 3.8 and the dependencies is the free Anaconda:

https://www.anaconda.com/download





### Needed libraries:

Whether you installed Anaconda or are using your own custom python, 
you should make sure you have all of the needed packages. The package uses various
non-standard Python libraries. Here's a list of all the needed libraries:


o	Numpy

o	os

o	Matplotlib

o	Statistics

o	Sklearn

o	Scipy

o	Pandas

o	afmformats (https://afmformats.readthedocs.io/en/latest/ ) 

-->  For quick install : `pip install afmformats`

o	nptdms (https://nptdms.readthedocs.io/en/stable/ )

-->  Quick installation via command line: `pip install npTDMS`






**_Note that it is recomanded to create a virtual environment for each software package. 
A virtual environment manages python requirements and versions and it is very useful if you
are working on or want to use different parallel packages/projects._**


- To create a virtual anaconda environment :

`conda create -n yourenvname python=x.x anaconda`

- To activate the environment:

`conda activate yourenvname`

- To deactivate the environment:

`conda deactivate yourenvname`

- To install a package in the environment:

`conda install -n yourenvname [package]`

- To delete the environment:

`conda remove -n yourenvname -all`






## **To install/run the software on your local machine :**

`git clone https://gitlab.com/ismahene_mesbah/afm_fs_software.git`


Once you clone the package. Run on the terminal the following:

`cd afm_fs_software/`

`cd Code/`

`python interface.py`





##### For detailed tutrorial refer to the file [`Tutorial_AFM_FS_Software.pdf`](Tutorial_AFM_FS_Software.pdf) above

