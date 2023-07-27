import os
import psutil

PROCNAME = "geckodriver" # or chromedriver or IEDriverServer
for proc in psutil.process_iter():
    # check whether the process name matches
    if proc.name() == PROCNAME:
        proc.kill()
