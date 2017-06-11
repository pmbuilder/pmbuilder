#!/usr/bin/env python3

"""
Copyright 2017 Oliver Smith

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


# Config
dir_pmbootstrap = "/home/user/code/pmbootstrap"
dir_staging = "/home/user/code/pmOS-binary-packages-staging"
packages = {"hello-world": ["x86_64"]}

# Imports
import sys
import os
import logging
sys.path.append(dir_pmbootstrap)
import pmb.aportgen
import pmb.helpers.run
import pmb.helpers.logging
import pmb.chroot.shutdown
import pmb.build

# Initialize args
sys.argv = ["pmbootstrap.py", "chroot"]
args = pmb.parse.arguments()
pmb.helpers.logging.init(args)

# Reset local copy of staging repo
if not os.path.exists(dir_staging):
    raise RuntimeError("Please clone the staging repo into this folder"
                       " first: " + dir_staging)
os.chdir(dir_staging)
pmb.helpers.run.user(args, ["git", "reset", "--hard", "origin/master"])

# Copy staging repo to work/packages
pmb.chroot.shutdown(args)
if os.path.exists(args.work + "/packages"):
    pmb.helpers.run.root(args, ["rm", "-r", args.work + "/packages"])
pmb.helpers.run.user(args, ["cp", "-r", dir_staging, args.work + "/packages"])
pmb.chroot.root(args, ["chown", "-R", "user", "/home/user/packages"])

# Build the first outdated package
for pkgname, architectures in packages.items():
    for arch in architectures:
        # Skip up-to-date packages (FIXME: suffix parameter is unnecessary!)
        aport = pmb.build.find_aport(args, pkgname)
        apkbuild = pmb.parse.apkbuild(aport + "/APKBUILD")
        if not pmb.build.other.is_necessary(args, "native", arch, apkbuild):
            print(pkgname + " (" + arch + "): up to date")
            continue

        # Build with deviceinfo
        print(pkgname + " (" + arch + "): building...")
        pmb.build.package(args, pkgname, arch, force=True,
                          recurse=False, buildinfo=True)

        # Copy the packages folder back
        pmb.helpers.run.user(args, ["rm", "-rf", dir_staging])
        pmb.helpers.run.user(args, ["cp", "-r", args.work + "/packages",
                                    dir_staging])

        # Challenge the build, so we know it is reproducible
        apk_path_relative = (arch + "/" + pkgname + "-" +
                             apkbuild["pkgver"] + "-r" +
                             apkbuild["pkgrel"] + ".apk")
        pmb.build.challenge(args, dir_staging + "/" + apk_path_relative)

        # Commit
        os.chdir(dir_staging)
        pmb.helpers.run.user(args, ["git", "add", "-A"])
        pmb.helpers.run.user(args, ["git", "commit", "-m",
                                    apk_path_relative])

        # We're done!
        logging.info("Next steps:")
        logging.info("1. Run 'git push' in " + dir_staging)
        logging.info("2. [Ask a postmarketOS admin to] trigger the"
                     " Travis CI job, that verifies the package and"
                     " pushes it to the real repository on success.")
        logging.info("3. Run pmbuilder.py again, until there are no"
                     " packages left, that need to be rebuilt.")
        sys.exit(0)
