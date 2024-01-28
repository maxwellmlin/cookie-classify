import os
import config

slurm_log_path = 'slurm_logs'
shFileName = '.temp_run.sh'

if not os.path.exists(slurm_log_path):
    os.mkdir(slurm_log_path)

results_path = config.CRAWL_PATH + 'results.json'
with open(results_path, 'w') as results:
    results.write("{}")

def sbatchRun(command, commandName, jobs, memory):
    shFile = [
        "#!/bin/bash",
        "#SBATCH --array=1-%d" % jobs,
        "#SBATCH --cpus-per-task=2",
        "#SBATCH --mem-per-cpu=%dG" % memory,
        "#SBATCH --job-name=%s" % commandName,
        f"#SBATCH -o /dev/null",
        f'#SBATCH -e /dev/null',

        "eval \"$(command conda 'shell.bash' 'hook' 2> /dev/null)\"",
        "conda activate cookie-classify",
        
        command
        ]

    with open(shFileName, 'w') as f:
        f.write('\n'.join(shFile))

    print(f'Running {commandName}.')
    os.system('sbatch %s' % shFileName)

jobs = 25
memory = 3
sbatchRun(f'python3 -u main.py --jobs {jobs}', commandName='cookie', jobs=jobs, memory=memory)