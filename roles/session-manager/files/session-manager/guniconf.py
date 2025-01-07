import multiprocessing

#
# Gunicorn config file
#
wsgi_app = "main:app"

# Server Mechanics
# ========================================
# current directory
chdir = "/root/session-manager"

# daemon mode
daemon = False

# Server Socket
# ========================================
bind = "0.0.0.0:80"

# Worker Processes
# ========================================
workers = multiprocessing.cpu_count() * 2 + 1

# Server Logging
# ========================================
accesslog = "-"
errorlog = "-"
loglevel = "info"
