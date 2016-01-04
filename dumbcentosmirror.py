#!/usr/bin/env python
import click
import requests
from bs4 import BeautifulSoup
import subprocess
from fcntl import flock, LOCK_EX, LOCK_NB
import os
import sys


def random_mirror(region):
    import StringIO
    import csv
    import random
    res = requests.get("http://www.centos.org/download/full-mirrorlist.csv")
    csvfile = StringIO(res.text)
    mirror = random.choice(
        [row for row in csv.DictReader(csvfile) if row['rsync mirror link'] and row['Region'] == region])
    return mirror['rsync mirror link'], mirror['http_mirror_link']


def scrape_index_by_major(mirror, major):
    res = requests.get(mirror)
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
               "{mirror}/{release}/".format(mirror=mirror, release=release),
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
@click.option('--http-mirror')
@click.option('--rsync-mirror')
@click.option('--region', default="US")
@click.option('--major', default="7")
@click.option('--newest-only/--no-newest-only', default=False)
@click.option('--dest-path', default='.')
@click.option('--nope/--no-nope', '-n', default=False)
def main(http_mirror, rsync_mirror, region, major, newest_only, dest_path, nope):
    if not http_mirror or not rsync_mirror:
        http_mirror, rsync_mirror = random_mirror(region)
    my_lock = lock(dest_path)
    releases = scrape_index_by_major(http_mirror, major)
    if newest_only:
        releases = [sorted(releases)[-1]]
    for release in releases:
        if nope:
            print "Totally would have fetched {0}".format(release)
        else:
            print "Fetching {0}".format(release)
            clone(rsync_mirror, release, dest_path)
    unlock(my_lock)

if __name__ == '__main__':
    main()
