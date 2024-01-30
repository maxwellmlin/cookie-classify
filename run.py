import os
import config
import yaml
import argparse
import pathlib

SLURM_LOG_PATH = 'slurm_logs'

def init():
    """
    Initialize everything needed for all workers.
    """
    # Create directory for slurm logs
    if not os.path.exists(SLURM_LOG_PATH):
        os.mkdir(SLURM_LOG_PATH)

    # Create crawl path
    pathlib.Path(config.CRAWL_PATH).mkdir(parents=True, exist_ok=False)

    # Initialize sites.json
    with open(config.CRAWL_PATH + 'sites.json', 'w') as results:
        results.write("{}")
        
    # Initialize meta.yaml
    meta = {
        "CRAWL_NAME": config.CRAWL_NAME,
        "SITE_LIST_PATH": pathlib.Path(config.SITE_LIST_PATH).name,
        "NUM_CLICKSTREAMS": config.NUM_CLICKSTREAMS,
        "CLICKSTREAM_LENGTH": config.CLICKSTREAM_LENGTH,
    }
    with open(config.CRAWL_PATH + 'meta.yaml', 'w') as outfile:
        yaml.dump(meta, outfile, default_flow_style=False)
        
    # Copy sites.txt to crawl path
    os.system(f'cp {config.SITE_LIST_PATH} {config.CRAWL_PATH}')

def sbatchRun(command, jobName, jobs, memory, cpus):
    """
    Create a temporary bash script and run it with sbatch.

    Args:
        command: The command to run.
        commandName: The name of the command.
        jobs: The number of jobs to run.
        memory: The amount of memory to allocate to each job.
        cpus: The number of cpus to allocate to each job.
    """
    shFile = [
        "#!/bin/bash",
        "#SBATCH --array=1-%d" % jobs,
        "#SBATCH --cpus-per-task=%d" % cpus,
        "#SBATCH --mem-per-cpu=%dG" % memory,
        "#SBATCH --job-name=%s" % jobName,
        
        # All standard output is redundant since we log to file
        f"#SBATCH -o /dev/null",
        f'#SBATCH -e /dev/null',

        # Uncomment this line if something is breaking before the logger is initialized
        # f"#SBATCH -o {SLURM_LOG_PATH}/slurm-%j.out",

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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--jobs',
        type=int,
        required=True
    )
    args = parser.parse_args()
    
    init()
    sbatchRun(f'python3 main.py --jobs {args.jobs}', jobName='cookie', jobs=args.jobs, memory=3, cpus=2)