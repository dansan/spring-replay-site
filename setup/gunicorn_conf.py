from pathlib import Path
from multiprocessing import cpu_count

log_dir = Path.home() / 'logs'
if not log_dir.exists():
    print(f"Creating log dir {log_dir!s}...")
    log_dir.mkdir(0o750)

mode = 'wsgi'
working_dir = '/home/replays/'
user = 'replays'
group = 'replays'
bind = '127.0.0.1:8091'
workers = max(2, min(4, cpu_count()))
timeout = 60
reload = False
loglevel = 'debug'
capture_output = True
accesslog = str(log_dir / 'access.log')
errorlog = str(log_dir / 'error.log')
syslog = False
proc_name = 'replays'
