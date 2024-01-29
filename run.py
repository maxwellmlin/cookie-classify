import os
import config
import yaml

slurm_log_path = 'slurm_logs'
shFileName = '.temp_run.sh'

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