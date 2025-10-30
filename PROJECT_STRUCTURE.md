# Project Structure

This repository is organized as follows:

- **README.md**: Main project overview, setup, and usage instructions.
- **PROBLEMS.md**: Issue tracking, root cause analyses, and configuration change history.
- **command.md**: Command-line usage, job submission, and monitoring instructions.
- **result.md**: Results and metrics from experiments.
- **OPTIMIZATION.md**: Rationale and notes on optimization strategies.
- **CONTRIBUTING.md**: Contribution guidelines.
- **.gitignore**: Excludes logs, outputs, and temporary files from version control.

## Source Code
- **pidsmaker/**: Main source code for the framework, organized into modules:
  - `encoders/`, `decoders/`, `detection/`, `featurization/`, `preprocessing/`, `triage/`, `utils/`, etc.
  - Each submodule contains relevant classes and functions for model components.

## Configuration
- **config/**: All configuration YAML files for models and experiments.
  - `default.yml`, `orthrus.yml`, `kairos.yml`, `magic.yml`, etc.
  - `experiments/`, `tuned_baselines/`, `tuned_components/`: Specialized configs for experiments and tuning.

## Scripts
- **scripts/**: All Slurm job scripts and utility scripts.
  - `run_*.slurm`: Slurm job submission scripts for each model/dataset/config.
  - `run.sh`, `run_all_datasets.sh`, `submit_all_e3_jobs.sh`: Batch and utility runners.
  - `monitor_job.sh`, `sync_wandb_run.sh`: Monitoring and sync utilities.
  - `python/`: Helper Python scripts for job automation.

## Data & Results
- **Ground_Truth/**: Ground truth datasets and reference files.
- **results/**: (Recommended) Store all experiment outputs and logs here.
- **artifacts/**, **wandb/**: (Ignored) Output and monitoring artifacts.

## Documentation
- **docs/**: Extended documentation, guides, and build scripts.
  - `docs/`: Markdown docs, images, and assets for the documentation site.
  - `mkdocs.yml`: MkDocs configuration.

## Tests
- **tests/**: All test scripts and test framework files.

## Miscellaneous
- **Dockerfile**, **compose-*.yml**: Containerization and orchestration files.
- **postgres/**: PostgreSQL initialization scripts.
- **settings/**: Additional scripts and settings.
- **.env**, **.env.local**: Environment variable files (ignored).

---

> **Tip:** All logs, outputs, and temporary files are excluded from version control via `.gitignore`. Place all experiment results in `results/` for easy tracking and archiving.

---

This structure ensures clarity, modularity, and ease of navigation for both users and contributors.
