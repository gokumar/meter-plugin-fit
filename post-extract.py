#!/usr/bin/env python
# This script is called after the plugin files have been copied to the target host file system
from bootstrap import Bootstrap

if __name__ == "__main__":
  bootstrap = Bootstrap()
  bootstrap.setup()