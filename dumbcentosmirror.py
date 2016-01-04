#!/usr/bin/env python
import click
import requests
from bs4 import BeautifulSoup
import subprocess
from fcntl import flock, LOCK_EX, LOCK_NB
import os
import sys


def scrape_index_by_major(mirror, major):
    mirror_index = "http://{mirror}/CentOS/".format(mirror=mirror)
    res = requests.get(mirror_index)
    soup = BeautifulSoup(res.text, 'lxml')
    releases = []
    for link in soup.find_all('a'):
        if not link.string:
            continue
        name = link.string.strip().strip('/')
        if name[0] == str(major) and name != str(major):
            releases.append(link['href'].strip('/'))
    return releases

def clone(mirror, release, dest_path):
    command = ['rsync', '-avSHP', '--delete', '--exclude', 'local*', '--exclude', 'isos',
               "{mirror}::CentOS/{release}/".format(mirror=mirror, release=release),
               "{dest_path}/{release}".format(dest_path=dest_path, release=release)]
    print "Running: {0}".format(" ".join(command))
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        print "Awww crap.  Something went south: {0}".format(e)


def lock(dest_path):
    try:
        fd = os.open(dest_path, os.O_RDONLY)
    except OSError as e:
        print "Dest is broke: {0}".format(e)
        sys.exit(1)

    try:
        flock(fd, LOCK_EX | LOCK_NB)
    except IOError:
        print "Already running"
        sys.exit(0)

    return fd


def unlock(fd):
    os.close(fd)


@click.command()
@click.option('--mirror', default="mirror.rackspace.com")
@click.option('--major', default="7")
@click.option('--newest-only/--no-newest-only', default=False)
@click.option('--dest-path', default='.')
@click.option('--nope/--no-nope', '-n', default=False)
def main(mirror, major, newest_only, dest_path, nope):
    my_lock = lock(dest_path)
    releases = scrape_index_by_major(mirror, major)
    if newest_only:
        releases = [sorted(releases)[-1]]
    for release in releases:
        if nope:
            print "Totally would have fetched {0}".format(release)
        else:
            print "Fetching {0}".format(release)
            clone(mirror, release, dest_path)
    unlock(my_lock)

if __name__ == '__main__':
    main()
