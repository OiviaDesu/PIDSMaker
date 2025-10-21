# PIDSMaker

[![Documentation](https://img.shields.io/badge/docs-online-pink.svg)](https://ubc-provenance.github.io/PIDSMaker/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15603122.svg)](https://doi.org/10.5281/zenodo.15603122)
![GitHub License](https://img.shields.io/github/license/ubc-provenance/PIDSMaker?color=red)

[**Paper**](https://tfjmp.org/publications/2025-usenixsec-2.pdf) | [**Documentation**](https://ubc-provenance.github.io/PIDSMaker/) | [**Installation**](https://ubc-provenance.github.io/PIDSMaker/ten-minute-install/)

The first framework designed to build and experiment with provenance-based intrusion detection systems (PIDSs) using deep learning architectures.
It provides a single codebase to run most recent state-of-the-arts systems and easily customize them to develop new variants.

**Currently supported PIDSs**:
- Velox (USENIX Sec'25): [Sometimes Simpler is Better: A Comprehensive Analysis of State-of-the-Art Provenance-Based Intrusion Detection Systems](https://tfjmp.org/publications/2025-usenixsec-2.pdf)
- Orthrus (USENIX Sec'25): [ORTHRUS: Achieving High Quality of Attribution in Provenance-based Intrusion Detection Systems](https://www.usenix.org/system/files/conference/usenixsecurity25/sec25cycle1-prepub-103-jiang-baoxiang.pdf)
- R-Caid (IEEE S\&P'24): [R-CAID: Embedding Root Cause Analysis within Provenance-based Intrusion Detection](https://gangw.web.illinois.edu/rcaid-sp24.pdf)
- Flash (IEEE S\&P'24): [Flash: A Comprehensive Approach to Intrusion Detection via Provenance Graph Representation Learning](https://dartlab.org/assets/pdf/flash.pdf)
- Kairos (IEEE S\&P'24): [Kairos: Practical Intrusion Detection and Investigation using Whole-system Provenance](https://arxiv.org/pdf/2308.05034)
- Magic (USENIX Sec'24): [MAGIC: Detecting Advanced Persistent Threats via Masked Graph Representation Learning](https://www.usenix.org/system/files/usenixsecurity24-jia-zian.pdf)
- NodLink (NDSS'24): [NODLINK: An Online System for Fine-Grained APT Attack Detection and Investigation](https://arxiv.org/pdf/2311.02331)
- ThreaTrace (IEEE TIFS'22): [THREATRACE: Detecting and Tracing Host-Based Threats in Node Level Through Provenance Graph Learning](https://arxiv.org/pdf/2111.04333)

## Setup

### Clone the repo
```
git clone https://github.com/ubc-provenance/PIDSMaker.git
```

### 10-min Docker Install with DARPA TC/OpTC Datasets

We have made the installation of DARPA TC/OpTC easy and fast, simply follow [these guidelines](https://ubc-provenance.github.io/PIDSMaker/ten-minute-install/).

## Documentation

A comprehensive [documentation](https://ubc-provenance.github.io/PIDSMaker/) is available, explaining all possible arguments and providing examples on how integrating new systems.

## Basic usage of the framework

Once you have a shell in the pids container, experiments can be run in multiple ways.

- Replace `SYSTEM` by `velox | orthrus | nodlink | threatrace | kairos | rcaid | flash | magic`.
- Replace `DATASET` by `CLEARSCOPE_E3 | CADETS_E3 | THEIA_E3 | CLEARSCOPE_E5 | THEIA_E5 | optc_h201 | optc_h501 | optc_h051`.

1. Run in the shell, no W&B:
    ```shell
    python pidsmaker/main.py SYSTEM DATASET --tuned
    ```

2. Run in the shell, monitored to W&B:
    ```shell
    python pidsmaker/main.py SYSTEM DATASET --tuned --wandb
    ```

3. Run in background, monitored to W&B (ideal for multiple parallel runs):
    ```shell
    ./run.sh SYSTEM DATASET --tuned
    ```

You can still watch the logs in your shell using `tail -f nohup.out`

**Warning:** Before performing evaluations, you should tune all systems. Follow the [instructions](https://ubc-provenance.github.io/PIDSMaker/features/tuning/) available in our documentation.

## Step-by-step: run Orthrus with Apptainer on an HPC cluster

The commands below mirror what we use on OzSTAR (Slurm + Apptainer + PostgreSQL 17). Adjust paths if your shared storage is different.

### 1. Prepare workspace and database

1. Clone the repository on your home or project space and enter it.
2. Pick a base directory on shared storage (for example `/fred/<project>/<user>`) and create the runtime folders:
    ```bash
    export BASE=/fred/<project>/<user>
    mkdir -p "$BASE"/{containers,pids_logs,pids_artifacts,.apptainer/{cache,tmp},pg/{data,logs}}
    ```
3. Install PostgreSQL 17 in a lightweight environment (conda/mamba works well):
    ```bash
    mamba create -n pg17 postgresql=17 -c conda-forge -y
    ~/.conda/envs/pg17/bin/initdb -D "$BASE/pg/data"
    ```
4. Start the server once on the login node, create the database, and restore the CADETS_E3 dump (replace the path with your copy):
    ```bash
    ~/.conda/envs/pg17/bin/pg_ctl -D "$BASE/pg/data" -l "$BASE/pg/logs/postgres.log" start
    ~/.conda/envs/pg17/bin/createdb -h 127.0.0.1 -U postgres cadets_e3
    ~/.conda/envs/pg17/bin/pg_restore -h 127.0.0.1 -U postgres -d cadets_e3 /path/to/cadets_e3.dump
    ~/.conda/envs/pg17/bin/pg_ctl -D "$BASE/pg/data" stop
    ```

### 2. Build the Apptainer image (one-time)

1. Load Apptainer on the login node (`module load apptainer` on OzSTAR).
2. Build the CUDA 11.7 image shipped with this repo:
    ```bash
    apptainer build "$BASE/containers/pidsmaker_cuda117.sif" containers/pidsmaker_cuda117.def
    ```
    The definition installs PyTorch 1.13.1+cu117, PyG 2.5.3, psycopg2, and pre-downloads NLTK data so jobs do not need outbound network access.

### 3. Configure environment for jobs

1. Create a `.env` file in the repo root for optional Weights & Biases usage:
    ```bash
    WANDB_MODE=offline
    WANDB_PROJECT=pidsmaker-orthus
    # WANDB_API_KEY=... (only if you plan to sync online after the run)
    ```
2. (Optional) Tune or copy a configuration – we use `config/orthrus_tuned.yml` for faster runs and `config/orthrus_aggressive.yml` to experiment with thresholds.

### 4. Submit jobs with Slurm + Apptainer

The scripts in `scripts/` stage PostgreSQL to node-local storage, launch the container with `--nv` (for GPUs), and package logs/artifacts at the end.

#### GPU job (A100 example)

```bash
sbatch scripts/run_orthus_cadets_e3_apptainer.slurm
```

- Requests 1 GPU, 4 CPUs, 64 GB RAM, and 50 GB node-local `/tmp` space.
- Uses Apptainer image at `$BASE/containers/pidsmaker_cuda117.sif`.
- Runs `python -m pidsmaker.main orthrus_aggressive CADETS_E3` by default (edit the script to switch configs/datasets).
- Outputs live logs under `~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out` and packages artifacts to the same directory.

#### CPU-only job

```bash
sbatch scripts/run_orthus_cadets_e3.slurm
```

- Uses the same Postgres + artifact handling but runs on a CPU partition (no `--nv`).
- Ideal for quick debugging before switching back to GPU.

#### Monitoring tips

```bash
squeue -j <JOBID>
tail -f ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out
```

When the job finishes you will find:
- Container console log and nvidia-smi sampling in `~/slurm-logs/`.
- Packaged artifacts (wandb offline run, env snapshot, pipeline log).
- PostgreSQL log for the node-local instance used during the job.

This setup reproduces the workflow we use to run Orthrus on CADETS_E3 end-to-end in about 35 minutes per GPU job.

## Citation

If you use this work, please cite the following paper:
```
@inproceedings{bilot2025simpler,
	title={{Sometimes Simpler is Better: A Comprehensive Analysis of State-of-the-Art Provenance-Based Intrusion Detection Systems}},
	author={Bilot, Tristan and Jiang, Baoxiang and  Li, Zefeng and  El Madhoun, Nour and Al Agha, Khaldoun and Zouaoui, Anis and Pasquier, Thomas},
	booktitle={Security Symposium (USENIX Sec'25)},
	year={2025},
	organization={USENIX}
}
```

## Contributing

Pull requests are welcome! Please follow the [contribution guidelines](https://ubc-provenance.github.io/PIDSMaker/contributing/).

## License

See [licence](LICENSE).
