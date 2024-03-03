import os
import argparse

SLURM_LOG_PATH = 'slurm_logs'

def sbatchRun(command, jobName):
    """
    Create a temporary bash script and run it with sbatch.

    Args:
        command: The command to run.
        commandName: The name of the command.
        jobs: The number of jobs to run.
        memory: The amount of memory to allocate to each job.
        cpus: The number of cpus to allocate to each job.
    """
    # Create directory for slurm logs
    if not os.path.exists(SLURM_LOG_PATH):
        os.mkdir(SLURM_LOG_PATH)
    
    shFile = [
        "#!/bin/bash",
        "#SBATCH --job-name=%s" % jobName,
        "#SBATCH --mem=8G",
        "#SBATCH --cpus-per-task=2",
        
        f"#SBATCH -o {SLURM_LOG_PATH}/slurm-%j.out",

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

    # subprocess.run(f'python3 main.py --jobs {args.jobs}', shell=True)
    sbatchRun(f'python3 -u {args.script}', jobName=args.script)
    
