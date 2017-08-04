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

def packages(arch_native, arch_devices):
    ret = {}

    # dependency test first
    for pkgname in ["hello-world", "hello-world-wrapper"]:
        ret[pkgname] = arch_native

    # native only
    for pkgname in [
        "0xffff",
        "ccache-cross-symlinks",
        "gcc-cross-wrappers",
        "heimdall",
        "postmarketos-splash",
        "postmarketos-mkinitfs",
        "postmarketos-mkinitfs-hook-usb-shell",
        "postmarketos-base",
        "qemu-user-static-repack",
    ]:
        ret[pkgname] = arch_native

    # native only, cross-compiler related
    for arch in arch_devices:
        for pkgname in ["musl", "binutils", "gcc", "busybox-static"]:
            ret[pkgname + "-" + arch] = arch_native

    # native and device
    for pkgname in ["mkbootimg", "unpackbootimg"]:
       ret[pkgname] = arch_devices + arch_native

    # device only
    for pkgname in ["weston", "postmarketos-demos"]:
        ret[pkgname] = arch_devices

    # plasma-mobile:
    for pkgname in [
        "extra-cmake-modules",
        "karchive",
        "qt5-qtscript-dev",
        "kdecoration",
        "autoconf-archive",
        "libyaml",
        "kwindowsystem",
        "kwidgetsaddons",
        "kitemviews",
        "kcoreaddons",
        "kunitconversion",
        "kitemmodels",
        "libutemper",
        "kwayland",
        "poppler-qt5",
        "kdoctools",
        "kfilemetadata",
        "kidletime",
        "polkit-qt5",
        "kcrash",
        "kdbusaddons",
        "kcodecs",
        "kconfig",
        "kpackage",
        "networkmanager-qt",
        "kservice",
        "solid",
        "media-player-info",
        "kauth",
        "kguiaddons",
        "kconfwidgets",
        "kiconthemes",
        "kcompletion",
        "sonnet",
        "ktextwidgets",
        "kglobalaccel",
        "kxmlgui",
        "kbookmarks",
        "kjobwidgets",
        "kio",
        "kactivitymanagerd",
        "knotifyconfig",
        "kjs",
        "kactivities",
        "kdeclarative",
        "knotifications",
        "plasma-framework",
        "cln",
        "kemoticons",
        "kinit",
        "kded",
        "kparts",
        "kpeople",
        "kjsembed",
        "kdesignerplugin",
        "kdelibs4support",
        "frameworkintegration",
        "kpty",
        "kdesu",
        "kcmutils",
        "ktexteditor",
        "threadweaver",
        "krunner",
        "kscreenlocker",
        "breeze",
        "kwin",
        "milou",
        "baloo",
        "plasma-workspace",
        "plasma-mobile",
        "farstream",
        "telepathy-glib",
        "telepathy-farstream",
        "telepathy-qt5",
        "plasma-phone-components"
    ]:
        ret[pkgname] = arch_native + arch_devices

    return ret
