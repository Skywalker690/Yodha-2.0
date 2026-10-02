# Build only after the operator has reviewed/accepted the separate FSL terms.
FROM mambaorg/micromamba:2.0.5
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 libsm6 libxext6 && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER
RUN micromamba install -y -n base -c https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/ -c conda-forge python=3.10 fsl-flirt fsl-bet2 fsl-avwutils fsl-data_standard && micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1
RUN python -m pip install --no-cache-dir torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir numpy==1.26.4 scipy==1.12.0 matplotlib==3.8.4 nibabel==5.2.1 h5py==3.10.0 nipype==1.8.6 scikit-image==0.22.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends bc dc && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER
COPY --chown=1000:1000 upstream /opt/avra
ENV FSLDIR=/opt/conda FSLOUTPUTTYPE=NIFTI OMP_NUM_THREADS=2 MPLCONFIGDIR=/tmp/matplotlib
ENV PATH=/opt/conda/bin:$PATH
RUN python /opt/avra/avra.py --help && test -f /opt/conda/data/standard/MNI152_T1_1mm.nii.gz && command -v flirt && command -v bet && command -v fslreorient2std
WORKDIR /opt/avra
