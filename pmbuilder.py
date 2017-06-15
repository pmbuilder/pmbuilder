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
import pmb.parse.other

# Parse own arguments
parser = argparse.ArgumentParser(prog="pmbuilder")
parser.add_argument("--no-reset", help="don't reset repo hard to orign/master and clean"
                    "all untracked files (bring the repo in the same state as"
                    "uploaded)", action="store_false", dest="reset")
args_pmbuilder = parser.parse_args()

# packages: native only
packages = {"hello-world": arch_native}
for pkgname in [
    "0xffff",
    "ccache-cross-symlinks",
    "gcc-cross-wrappers",
    "heimdall",
    "postmarketos-base",
    "postmarketos-demos",
    "postmarketos-mkinitfs",
    "postmarketos-mkinitfs-hook-usb-shell",
    "qemu-user-static-repack",
]:
    packages[pkgname] = arch_native

# packages: cross-compilers (native only)
for arch in arch_devices:
    for pkgname in ["musl", "binutils", "gcc"]:
        packages[pkgname + "-" + arch] = arch_native

# packages: native and device
for pkgname in ["mkbootimg", "unpackbootimg"]:
    packages[pkgname] = arch_devices + arch_native

# packages: device only
for pkgname in ["weston"]:
    packages[pkgname] = arch_devices

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

    # Restore the file extension, fix ownership
    for apk in glob.glob(args.work + "packages/*/*.apk.unverified"):
        os.rename(apk, apk[:-len(".unverified")])
    pmb.chroot.root(args, ["chown", "-R", "user", "/home/user/packages"])

# Build the first outdated package
for pkgname, architectures in packages.items():
    for arch in architectures:
        # Skip up-to-date packages
        aport = pmb.build.find_aport(args, pkgname)
        apkbuild = pmb.parse.apkbuild(aport + "/APKBUILD")
        apkindex_path = dir_staging + "/" + arch + "/APKINDEX.tar.gz"
        if not pmb.build.other.is_necessary(args, arch, apkbuild,
                                            apkindex_path):
            print(pkgname + " (" + arch + "): up to date")
            continue

        # Build with buildinfo
        print(pkgname + " (" + arch + "): building...")
        repo_before = pmb.helpers.repo.files(args)
        pmb.build.package(args, pkgname, arch, force=True,
                          recurse=False, buildinfo=True)
        repo_diff = pmb.helpers.repo.diff(args, repo_before)

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
        pmb.build.challenge(args, dir_staging + "/" + apk_path_relative)

        # Change the file extension to .apk.unverified
        for apk in glob.glob(dir_staging + "/*/*.apk"):
            os.rename(apk, apk + ".unverified")

        # Write down the last changed file
        with open(dir_staging + "/last_modified.txt", "w") as handle:
            handle.write(apk_path_relative + "\n")

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


logging.info("Nothing to do, all packages are up to date!")
sys.exit(1)
