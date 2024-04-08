import os
import argparse
import config

def sbatch_run(command: str, job_name: str, memory: int, cpus: int):
    """
    Create a temporary bash script and run it with sbatch.

    Args:
        command: The command to run.
        job_name: The name of the job.
        memory: The amount of memory to allocate to each job.
        cpus: The number of cpus to allocate to each job.
    """
    # Create directory for slurm logs
    if not os.path.exists(config.SLURM_LOG_PATH):
        os.mkdir(config.SLURM_LOG_PATH)
    
    shFile = [
        "#!/bin/bash",
        "#SBATCH --array=0-24",
        "#SBATCH --cpus-per-task=%d" % cpus,
        "#SBATCH --mem-per-cpu=%dG" % memory,
        "#SBATCH --job-name=%s" % job_name,
        "#SBATCH --time=28-00:00:00",
        
        f"#SBATCH -o {config.SLURM_LOG_PATH}/slurm-%j.out",

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
    parser.add_argument("script", help="Script to submit to slurm.")
    args = parser.parse_args()

    sbatch_run(f'python3 -u {args.script}', job_name=args.script, memory=4, cpus=2)
