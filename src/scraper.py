import urllib3

# Create a PoolManager instance
http = urllib3.PoolManager()

# Change made here
allowed_methods=["HEAD", "GET", "OPTIONS"]

# Other code...
