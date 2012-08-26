#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info, platform, prefix

version = "0.1.0"
deps = ["pbs", "PrettyTable", "livestreamer"]

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

setup(name="livestreamermanager",
      version=version,
      description="A manager for the livestreamer program",
      url="https://github.com/niallm90/livestreamermanager",
      author="Niall McAndrew",
      author_email="niallm90@gmail.com",
      license="BSD",
      packages=["livestreamermanager"],
      package_dir={'': 'src'},
      entry_points={
          "console_scripts": ['lsm=livestreamermanager.cli:main']
      },
      install_requires=deps,
      classifiers=["Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Environment :: Console",
                   "Development Status :: 5 - Production/Stable",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Utilities"],
      dependency_links = ['https://github.com/chrippa/livestreamer/tarball/master#egg=livestreamer-1.2.0']
)

# Fix the entry point so that we don't end up in an infinite loop because of multiprocess
if platform == 'win32':
    f = open(prefix + "\\Scripts\\lsm-script.py", "r+")
    
    contents = f.readlines()

    push = False
    output = ""
    for index, line in enumerate(contents):
        if push:
            line = " " + line;

        if "sys.exit(" in line:
            line = "if __name__ == '__main__':\n " + line;
            push = True
    
        if line == " )\n":
            push = False

        output = output + line

    f.seek(0)
    f.write(output)
    f.close()

