# What to do if a worker hangs

1. Check the log file. If the last timestamp is more than 1 hour behind the current time, the worker has hanged.
2. Use `squeue -u mml66 | grep <task-id>` to get the job ID
3. Run `scancel <job-id>` to stop the worker
4. If the last logged domain is not in `results.json`, the crawl was incomplete
    1. Delete the domain directory
    2. Use `python inject.py` to inject the incomplete domain back into the queue
5. Use `python run.py --jobs <task-id> --skip-init` to restart the worker