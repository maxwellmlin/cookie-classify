import os
import config
import yaml
import argparse
import pathlib
from filelock import Timeout, FileLock
import json

def init():
    """
    Initialize everything needed for all workers.
    """
    # Create crawl path
    pathlib.Path(config.DATA_PATH).mkdir(parents=True, exist_ok=False)

    # Initialize results
    with open(config.RESULTS_PATH, 'w') as f:
        f.write("{}")
        
    # Initialize meta.yaml
    config_dict = {
        "CRAWL_NAME": config.CRAWL_NAME,
        "SITE_LIST_PATH": config.DATA_PATH + pathlib.Path(config.SITE_LIST_PATH).name,
        "TOTAL_ACTIONS": config.TOTAL_ACTIONS,
        "CLICKSTREAM_LENGTH": config.CLICKSTREAM_LENGTH,
        "WAIT_TIME": config.WAIT_TIME,
        "DATA_PATH": config.DATA_PATH,
        "RESULTS_PATH": config.RESULTS_PATH,
        "QUEUE_PATH": config.QUEUE_PATH,
        "CONFIG_PATH": config.CONFIG_PATH,
    }
    with open(config.CONFIG_PATH, 'w') as outfile:
        yaml.dump(config_dict, outfile, default_flow_style=False)
        
    # Copy sites.txt to crawl path
    os.system(f'cp {config.SITE_LIST_PATH} {config.DATA_PATH}')

    # Write sites to queue with lock
    sites = []
    with open(config.SITE_LIST_PATH) as file:
        for line in file:
            sites.append(line.strip())
    queue_path = config.QUEUE_PATH
    queue_lock = FileLock(queue_path + '.lock', timeout=10)
    with queue_lock:
        with open(queue_path, 'w') as f:
            json.dump(sites, f)

def sbatch_run(command: str, job_name: str, jobs: str, memory: int, cpus: int):
    """
    Create a temporary bash script and run it with sbatch.

    Args:
        command: The command to run.
        job_name: The name of the job.
        jobs: The number of jobs to run. Must be in array format (e.g. 1-25).
        memory: The amount of memory to allocate to each job.
        cpus: The number of cpus to allocate to each job.
    """
    # Create directory for slurm logs
    if not os.path.exists(config.SLURM_LOG_PATH):
        os.mkdir(config.SLURM_LOG_PATH)
    
    shFile = [
        "#!/bin/bash",
        "#SBATCH --array=%s" % jobs,
        "#SBATCH --cpus-per-task=%d" % cpus,
        "#SBATCH --mem-per-cpu=%dG" % memory,
        "#SBATCH --job-name=%s" % job_name,
        "#SBATCH --time=28-00:00:00",
        
        # All standard output is redundant since we log to file
        f"#SBATCH -o /dev/null",
        f'#SBATCH -e /dev/null',

        # Uncomment this line if something is breaking before the logger is initialized
        # f"#SBATCH -o {config.SLURM_LOG_PATH}/slurm-%j.out",

        # Load conda environment
        "eval \"$(command conda 'shell.bash' 'hook' 2> /dev/null)\"",
        "conda activate cookie-classify",
        
        command
        ]

    # Create temporary bash script
    shFileName = '.temp_run.sh'
    with open(shFileName, 'w') as f:
        f.write('\n'.join(shFile))

    # Run bash script with sbatch
    os.system('sbatch %s' % shFileName)

if __name__ == "__main__":    
    if input("This is a destructive action if worker arrays are not disjoint. Are you sure you want to continue? (y/n) ") != "y":
        print("Exiting.")
        exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--jobs',
        type=str,
        required=True
    )
    parser.add_argument(
        '--skip-init',
        action='store_true',
    )
    args = parser.parse_args()
    
    if not args.skip_init:
        init()

    # subprocess.run(f'python3 main.py --jobs {args.jobs}', shell=True)
    sbatch_run(f'python3 main.py', job_name='cookie', jobs=args.jobs, memory=4, cpus=2)