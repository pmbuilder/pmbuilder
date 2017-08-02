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
arch_devices = ["armhf", "aarch64"]
arch_native = ["x86_64"]


# Imports
import sys
import os
import logging
import glob
import argparse
sys.path.append(dir_pmbootstrap)
import pmb.aportgen
import pmb.build
import pmb.chroot.shutdown
import pmb.helpers.run
import pmb.helpers.repo
import pmb.helpers.logging
import pmb.challenge

import packages


# Parse own arguments
parser = argparse.ArgumentParser(prog="pmbuilder")
parser.add_argument("--no-reset", help="don't reset repo hard to orign/master and clean"
                    "all untracked files (bring the repo in the same state as"
                    "uploaded)", action="store_false", dest="reset")
args_pmbuilder = parser.parse_args()

# Initialize args compatible to pmbootstrap
sys.argv = ["pmbootstrap.py", "chroot"]
args = pmb.parse.arguments()
setattr(args, "output_repo_changes", None)
pmb.helpers.logging.init(args)


# Reset local copy of staging repo
if not os.path.exists(dir_staging):
    raise RuntimeError("Please clone the staging repo into this folder"
                       " first: " + dir_staging)
os.chdir(dir_staging)
if args_pmbuilder.reset:
    pmb.helpers.run.user(args, ["git", "reset", "--hard", "origin/master"])
    pmb.helpers.run.user(args, ["git", "clean", "-d", "-x", "-f"])

    # Copy staging repo to work/packages
    pmb.chroot.shutdown(args)
    if os.path.exists(args.work + "/packages"):
        pmb.helpers.run.root(args, ["rm", "-r", args.work + "/packages"])
    pmb.helpers.run.user(
        args, ["cp", "-r", dir_staging, args.work + "/packages"])

    # Remove files, that confuse pmbootstrap's repo indexing
    for pattern in ["last_modified.txt", "*.pub", "README.md"]:
        for file in glob.glob(args.work + "/packages/" + pattern):
            pmb.helpers.run.user(args, ["rm", file])

    # Restore the file extension, fix ownership
    for apk in glob.glob(args.work + "/packages/*/*.apk.unverified"):
        os.rename(apk, apk[:-len(".unverified")])
    pmb.chroot.root(args, ["chown", "-R", "user", "/home/user/packages"])

# Build the first outdated package
packages = packages.packages(arch_native, arch_devices)
for pkgname, architectures in packages.items():
    for arch in architectures:
        # Skip up-to-date packages
        aport = pmb.build.find_aport(args, pkgname)
        apkbuild = pmb.parse.apkbuild(args, aport + "/APKBUILD")
        apkindex_path = dir_staging + "/" + arch + "/APKINDEX.tar.gz"
        if not pmb.build.other.is_necessary(args, arch, apkbuild,
                                            apkindex_path):
            print(pkgname + " (" + arch + "): up to date")
            continue

        # Build with buildinfo
        print(pkgname + " (" + arch + "): building...")
        repo_before = pmb.helpers.repo.files(args)
        pmb.build.package(args, pkgname, arch, force=True,
                          buildinfo=True)
        repo_diff = pmb.helpers.repo.diff(args, repo_before)

        # Remove old versions of the packages, that have just been built
        for file in repo_diff:
            file_without_version = "-".join(file.split("-")[:-2])
            for file in glob.glob(args.work + "/packages/" + file_without_version + "-*"):
                is_new = False
                for file_new in repo_diff:
                    if file.endswith(file_new):
                        is_new = True
                        break
                if not is_new:
                    file_relative = file[len(args.work + "/packages/"):]
                    logging.info("Remove old file: " + file_relative)
                    pmb.helpers.run.root(args, ["rm", file])
                    file_staging = dir_staging + "/" + file_relative
                    if file_staging.endswith(".apk"):
                        file_staging += ".unverified"
                    pmb.helpers.run.user(args, ["rm", file_staging])

        # Rebuild the APKINDEX files, so they do not include references to
        # outdated packages
        pmb.build.index_repo(args)

        # Copy back the files modified during the build
        for file in repo_diff:
            arch = os.path.dirname(file)
            pmb.helpers.run.user(
                args, ["mkdir", "-p", dir_staging + "/" + arch])
            pmb.helpers.run.user(args, ["cp", args.work + "/packages/" +
                                        file, dir_staging + "/" + file])

        # Challenge the build, so we know it is reproducible
        apk_path_relative = (arch + "/" + pkgname + "-" +
                             apkbuild["pkgver"] + "-r" +
                             apkbuild["pkgrel"] + ".apk")
        pmb.challenge.build(args, dir_staging + "/" + apk_path_relative)

        # Change the file extension to .apk.unverified
        for apk in glob.glob(dir_staging + "/*/*.apk"):
            os.rename(apk, apk + ".unverified")

        # Challenge all APKINDEX.tar.gz files in the staging repo
        for path_apkindex in glob.glob(dir_staging + "/*/APKINDEX.tar.gz"):
            pmb.challenge.apkindex(args, path_apkindex, ".unverified")

        # Write down the last built package
        with open(dir_staging + "/last_modified.txt", "w") as handle:
            handle.write(apk_path_relative + "\n")

        # Commit
        os.chdir(dir_staging)
        pmb.helpers.run.user(args, ["git", "add", "-A"])
        pmb.helpers.run.user(args, ["git", "status"])
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


logging.info("Nothing to do, all packages are up to date!")
sys.exit(1)

