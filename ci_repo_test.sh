#!/bin/sh
# This is a quick and dirty test script for the lazy reproducible builds binary
# package repository. Watch out for hardcoded paths and that all packages built
# with pmbootstrap get deleted (!)

set -e
export PYTHONIOENCODING=utf-8

# Work dir for the verification CI job
export DIR_WORK=~/.local/var/_ci_repo_test_pmbootstrap

# Copy binary-package-repo dir, and clear it
[ -d /tmp/_ci_verified ] && rm -rf /tmp/_ci_verified
cp -r ~/code/binary-package-repo /tmp/_ci_verified
rm -v /tmp/_ci_verified/*/APKINDEX.tar.gz /tmp/_ci_verified/*/*.apk || true
tree /tmp/_ci_verified

# Reset staging dir
STAGING=~/code/pmOS-binary-packages-staging
cd "$STAGING"
git reset --hard origin/master
rm -v */* || true

# Delete all packages
# $1: path to work dir
delete_packages_dir() {
	pmbootstrap --work="$1" shutdown
	PACKAGES="$1"/packages
	[ -d "$PACKAGES" ] && sudo rm -rf "$PACKAGES"
	mkdir -p "$PACKAGES/x86_64" "$PACKAGES/armhf" "$PACKAGES/aarch64"
	pmbootstrap --work="$1" chroot -- chown -R user:user /home/user/packages/
}

# Not sure if needed here
delete_packages_dir ~/.local/var/pmbootstrap

while true; do
	tree "$STAGING"
	tree "$PACKAGES"
	tree "/tmp/_ci_verified"
	echo "### RUN: PMBUILDER"
	~/code/pmbuilder/pmbuilder.py --no-reset

	# Prepare dir_local git repos
	echo "### PREPARE: VERIFY_RELEASE_PACKAGE"
	DIR_LOCAL=~/.local/var/pmOS-verify-release-package/
	[ -e "$DIR_LOCAL" ] && rm -rf "$DIR_LOCAL"
	mkdir -p "$DIR_LOCAL"
	cp -r "$STAGING" "$DIR_LOCAL"/repo_staging
	cp -r ~/code/pmbootstrap "$DIR_LOCAL"/pmbootstrap

	# Delete the currently built packages in the verification work folder
	delete_packages_dir "$DIR_WORK"

	# Copy the apk key of the pmbuilder to the verification work folder
	sudo cp -v ~/.local/var/pmbootstrap/config_apk_keys/user-*.rsa.pub \
		"$DIR_WORK"/config_apk_keys/

	# Copy release repo to temp and execute the script with the same log file
	# as the pmbuilder script uses, so it's easier to follow, but with a
	# different WORK folder, so a different set of apk keys gets used.
	cd /tmp/_ci_verified
	echo "### RUN: VERIFY_RELEASE_PACKAGE"
	export FILE_LOG=~/.local/var/pmbootstrap/log.txt
	./.travis/verify_release_package.sh
done
