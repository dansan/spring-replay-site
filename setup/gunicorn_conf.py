from multiprocessing import cpu_count

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
accesslog = '/home/replays/logs/access.log'
errorlog = '/home/replays/logs/error.log'
syslog = False
proc_name = 'replays'
