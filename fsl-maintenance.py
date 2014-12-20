#!/usr/bin/env python
#
# fsl-maintenance - A helper script to maintain the Security Lab package list
# and other relevant maintenance tasks.
#
# Copyright (c) 2012-2014 Fabian Affolter <fab@fedoraproject.org>
#
# All rights reserved.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Credits goes to Robert Scheck. He did a lot brain work for the initial
# approach. This script is heavy based on his perl scripts.

import argparse
import operator
import itertools
import datetime
import re
import sys
import os
try:
    import columnize
except ImportError:
    print 'Please install pycolumnize first -> sudo yum -y install pycolumnize'
import yum
try:
    import git
except ImportError:
    print 'Please install GitPython first -> sudo yum -y install GitPython'
try:
    import yaml
except ImportError:
    print 'Please install PyYAML first -> sudo yum -y install PyYAML'

repo = git.Repo(os.getcwd())

def getPackages():
    """
    Reading yaml package file which is placed in the root of the Fedora 
    Security Lab git repository.
    """
    file = open("pkglist.yaml", "r") 
    pkgslist = yaml.safe_load(file)
    file.close()
    return pkgslist

def display():
    """All included tools and details will be printed to STDOUT."""
    pkgslist = getPackages()

    pkgslistIn = []
    pkgslistEx = []
    pkgslistAll = []

    # All packages
    pkgslistAll = []
    for pkg in pkgslist:
        pkgslistAll.append(pkg['pkg'])

    # Split list of packages into included and excluded packages
    # Not used at the moment
    #for pkg in pkgslist:
	#    if 'exclude' in pkg:
	#        pkgslistEx.append(pkg['pkg'])
	#    else:
	#        pkgslistIn.append(pkg['pkg'])

    # Displays the details to STDOUT
    print '\nDetails about the packages in the Fedora Security Lab\n'
    print 'Packages in comps               : %s' % len(pkgslist)
    print 'Packages included in live media : %s\n' % len(pkgslistIn)
    print 'Package listing:'
    sorted_pkgslist = sorted(pkgslistAll)
    print columnize.columnize(sorted_pkgslist, displaywidth=72)

def raw():
    """The pkglist.yaml file will be printed to STDOUT."""
    pkgslist = getPackages()
    print yaml.dump(pkgslist)

def add(pkgname):
    """Adds a new package to the Fedora Security Lab."""
    print 'Not implemented at the moment. Package name was %s. Please edit ' \
          'the pkglist.yaml file by hand.' % pkgname

    categories = {"CodeAnalysis", 
        "Forensics",
        "IntrusionDetection",
        "NetworkStatistics",
        "PasswordTools",
        "Reconnaissance",
        "VoIP",
        "WebApplicationTesting",
        "Wireless"
        }
    for category in categories:
        print category

def edit(pkgname):
    """Modify an existing package in the package list."""
    print 'Not implemented at the moment. Package name was %s. Please edit ' \
          'the pkglist.yaml file by hand.' % pkgname

def comps():
    """
    Generates the entries to include into the comps-fXX.xml.in file.  
    <packagelist>
      ...
    </packagelist>
    """
    pkgslist = getPackages()

    # Split list of packages into eincluded and excluded packages
    sorted_pkgslist = sorted(pkgslist, key=operator.itemgetter('pkg'))
    for pkg in sorted_pkgslist:
	    print '      <packagereq type="default">%s</packagereq>' % pkg['pkg']

def playbook():
    """
    Generates a Ansible playbook for the installation of the Fedora Security
    Lab packages.
    """
    pkgslist = getPackages()

    part1 = """# This playbook installs all Fedora Security Lab packages.
#
# Copyright (c) 2013-2014 Fabian Affolter <fab@fedoraproject.org>
#
# All rights reserved.
# This file is licensed under GPLv2, for more details check COPYING.
#
# Generated by fsl-maintenance.py at %s
# 
# Usage: ansible-playbook fsl-packages.yml -f 10

---
- hosts: fsl_hosts
  user: root
  tasks:
  - name: install all packages from the FSL
    yum: pkg={{ item }}
         state=present 
    with_items:\n""" % (datetime.date.today())

    # Split list of packages into eincluded and excluded packages
    sorted_pkgslist = sorted(pkgslist, key=operator.itemgetter('pkg'))

    # Write the playbook files
    fileOut = open('ansible-playbooks/fsl-packages.yml','w')
    fileOut.write(part1)
    for pkg in sorted_pkgslist:
        fileOut.write('       - %s\n' %  pkg['pkg'])
    fileOut.close()

    # Commit the changed file to the repository
    repo.git.add('ansible-playbooks/fsl-packages.yml')
    repo.git.commit(m='update playbook')
    repo.git.push()

def live():
    """Generates the exclude list for the kickstart file."""
    pkgslist = getPackages()
    # Split list of packages into eincluded and excluded packages
    sorted_pkgslist = sorted(pkgslist, key=operator.itemgetter('pkg'))

    for pkg in sorted_pkgslist:
	    if pkg['exclude'] == 1:
	        print '-%s' % pkg['pkg']

def trac():
    # FIXME: There are still duplicates in the list !!!
    """Generates the package overview for the FSL trac instance."""
    pkgslist = getPackages()

    # Simplifiy the packages list, only package name and category are relevant
    # for the Trac wiki page
    pkgslistIn = []
    for pkg in pkgslist:
	    pkgslistIn.append((pkg['pkg'], pkg['category']))

    sorted_pkgslist = sorted(pkgslistIn, key=operator.itemgetter(1))
    groups = itertools.groupby(sorted_pkgslist, key=operator.itemgetter(1))
    sorted_categories = [{'category': k, 'pkgs': [x[0] for x in v]} for k, v in groups]
    #print sorted_categories

    yb = yum.YumBase()
    yb.conf.cache = 1
    print '<--- snip --->'
    for cat in sorted_categories:
        if cat['category'] != 'VoIP':
            elements = re.findall('[A-Z][^A-Z]*', cat['category'])
            category_name = ' '.join(elements)
        else:
            category_name = cat['category']
        print '== %s ==' % category_name
        for pkg in cat['pkgs']:
            pkgData = yb.pkgSack.searchNevra(pkg)
            for detail in pkgData:
#                print detail.name, detail.url
                part1 = '* [%s %s]' % (detail.url, detail.name)
                part2 = detail.summary
                part3 = '[https://admin.fedoraproject.org/pkgdb/acls/name/%s Fedora Package Database]' % detail.name
                part4 = '[https://admin.fedoraproject.org/pkgdb/acls/bugs/%s Bug Reports]' % detail.name
                entry =  part1 + " - " + part2 + " - " + part3 + " - " + part4
                print entry
    print '<--- snap --->\nPlease copy the text between the markings to the '
    print 'availableApps (https://fedorahosted.org/security-spin/wiki/availableApps) page in the Trac wiki.'

def menus():
    """
    Generator for the .desktop files which are used for the menu structure.
    All files are packaged in the security-menus RPM package.
    """
    pkgslist = getPackages()
    # Terminal is the standard terminal application of the Xfce desktop
    terminal = 'xfce4-terminal'

    # Collects all files in the directory
    filelist = []
    os.chdir('security-menu')
    for files in os.listdir("."):
        if files.endswith(".desktop"):
            filelist.append(files)
    # Write the .desktop files
    for pkg in pkgslist:
        if 'command' and 'name' in pkg:
            fileOut = open('security-' + pkg['pkg'] + '.desktop','w')
            fileOut.write('[Desktop Entry]\n')
            fileOut.write('Name=%s\n' %  pkg['name'])
            fileOut.write("Exec=%s -e \"su -c '%s; bash'\"\n" % (terminal, pkg['command']))
            fileOut.write('TryExec=%s\n' % pkg['pkg'])
            fileOut.write('Type=Application\n')
            fileOut.write('Categories=System;Security;X-SecurityLab;X-%s;\n' % pkg['category'])
            fileOut.close()

    # Compare the needed .desktop file against the included packages, remove
    # .desktop files from exclude packages
    dellist = filelist
    for pkg in pkgslist:
            if 'command' in pkg:
                dellist.remove('security-' + pkg['pkg'] + '.desktop')
            if 'exclude' in pkg:
                if pkg['exclude'] == 1:
                    dellist.append('security-' + pkg['pkg'] + '.desktop')

    # Remove the .desktop files which are no longer needed
    if len(dellist) != 0:
        for file in dellist:
	        os.remove(file)

def default():
    """Displayed if there are no given options."""
    pkgslist = getPackages()

    # Displays the details to STDOUT
    print '\nDetails about the packages in the Fedora Security Lab\n'
    print 'Packages in comps               : %s' % len(pkgslist)
    print '\nTo see all available options use -h or --help.'

def argParsing():
    parser = argparse.ArgumentParser(
	    description='This tool can be used for maintaining the Fedora Security Lab package list.',
	    epilog="Please report all bugs and comment.")
    parser.add_argument('-d', '--display',
                        action='store_true',
                        help='display the current included tools to STDOUT')
    parser.add_argument('-a', '--add',
                        help='add a new tool to the Fedora Security Lab')
    parser.add_argument('-e', '--edit',
                       help='editing a given entry')
    parser.add_argument('-c', '--comps',
                       action='store_true',
                       help='generates a package list for comps')
    parser.add_argument('-t', '--trac',
                       action='store_true',
                       help='generate an updated list for the incluction in trac')
    parser.add_argument('-m', '--menus',
                       action='store_true',
                       help='generate an updated list for the security-menus package')
    parser.add_argument('-l', '--live',
                       action='store_true',
                       help='generate an exclude list for the kickstart file')
    parser.add_argument('-r', '--raw',
                       action='store_true',
                       help='display the pkglist.yaml file to STDOUT')
    parser.add_argument('-p', '--playbook',
                       action='store_true',
                       help='generate a Ansible playbook for package installation')

    return parser.parse_args()

def main_run(argv):
    if len(argv) < 2:
        default()
        sys.exit(1)

    args = argParsing()
    if args.display:
        display()
    if args.add:
        add(args.add)
    if args.edit:
        edit(args.edit)
    if args.comps:
        comps()
    if args.trac:
        trac()
    if args.menus:
        menus()
    if args.live:
        live()
    if args.raw:
        raw()
    if args.playbook:
        playbook()

def main():
    """Main program entry point"""
    try:
        sys.exit(main_run(sys.argv))
    except KeyboardInterrupt:
        print 'Interrupted, exiting...'
        sys.exit(1)

if __name__ == '__main__':
    main()
