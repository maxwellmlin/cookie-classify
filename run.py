import os
import config
import yaml
import argparse
import pathlib

def init():
    """
    Initialize everything needed for all workers.
    """
    # Create directory for slurm logs
    slurm_log_path = 'slurm_logs'
    if not os.path.exists(slurm_log_path):
        os.mkdir(slurm_log_path)

    # Initialize sites.json
    with open(config.CRAWL_PATH + 'sites.json', 'w') as results:
        results.write("{}")
        
    # Initialize meta.yaml
    meta = {
        "CRAWL_NAME": config.CRAWL_NAME,
        "SITE_LIST_PATH": config.SITE_LIST_PATH,
        "NUM_CLICKSTREAMS": config.NUM_CLICKSTREAMS,
        "CLICKSTREAM_LENGTH": config.CLICKSTREAM_LENGTH,
    }
    with open(config.CRAWL_PATH + 'meta.yaml', 'w') as outfile:
        yaml.dump(meta, outfile, default_flow_style=False)
        
    # Create crawl path
    pathlib.Path(config.CRAWL_PATH).mkdir(parents=True, exist_ok=True)

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
    print(f'Running {jobName}.')
    os.system('sbatch %s' % shFileName)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--jobs',
        type=int,
        required=True
    )
    args = parser.parse_args()
    
    sbatchRun(f'python3 main.py --jobs {args.jobs}', jobName='cookie', jobs=args.jobs, memory=3, cpus=2)