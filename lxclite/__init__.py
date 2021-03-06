import subprocess
import os
import time

# LXC Python Library
# for compatibility with LXC 0.8 and 0.9
# on Ubuntu 12.04/12.10/13.04

# Author: Elie Deloumeau
# Contact: elie@deloumeau.fr

# The MIT License (MIT)
# Copyright (c) 2013 Elie Deloumeau

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

def _run(cmd, output=False):
    '''
    To run command easier
    '''
    if output:
        try:
            out = subprocess.check_output('{}'.format(cmd), shell=True)
        except subprocess.CalledProcessError:
            out = False
        return out
    return subprocess.check_call('{}'.format(cmd), shell=True) # returns 0 for True

class ContainerAlreadyExists(Exception): pass
class ContainerDoesntExists(Exception): pass
class ContainerAlreadyRunning(Exception): pass
class ContainerNotRunning(Exception): pass
class DirectoryDoesntExists(Exception): pass
class NFSDirectoryNotMounted(Exception): pass

def exists(container):
    '''
    Check if container exists
    '''
    if container in ls(): return True
    return False

def get_ipv4(container):
    '''
    Get the IPv4 address for a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exist!'.format(container))
    output = _run('lxc-ls --fancy {}'.format(container), output=True).splitlines()
    for l in output:
        parts = l.split()
        if parts[0] == container:
            return parts[2]
    return None

def create(container, template='ubuntu', storage=None, xargs=None):
    '''
    Create a container (without all options)
    Default template: Ubuntu
    '''
    if exists(container): raise ContainerAlreadyExists('Container {} already created!'.format(container))

    command = 'lxc-create -n {}'.format(container)
    command += ' -t {}'.format(template)
    if storage: command += ' -B {}'.format(storage)
    if xargs: command += ' -- {}'.format(xargs)

    return _run(command)


def clone(orig=None, new=None, snapshot=False):
    '''
    Clone a container (without all options)
    '''
    if orig and new:
        if exists(new): raise ContainerAlreadyExists('Container {} already exist!'.format(new))

        if snapshot:
            command = 'lxc-clone -s {} {}'.format(orig, new)
        else:
            command = 'lxc-clone {} {}'.format(orig, new)

        return _run(command)


def info(container):
    '''
    Check info from lxc-info
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exist!'.format(container))

    output = _run('lxc-info -qn {}'.format(container), output=True).splitlines()
    
    # on lxc 1.0 lxc-info output has been shifted
    state = output[1].split()[1]

    if state == 'STOPPED':
        pid = "0"
    else:
        pid = output[0].split()[1]

    return {'state': state,
            'pid': pid}


def ls():
    '''
    List containers directory

    Note: Directory mode for Ubuntu 12/13 compatibility
    '''
    lxcdir = '/var/lib/lxc/'
    ct_list = []

    try: 
	lsdir  = os.listdir(lxcdir)
	for i in lsdir:
    	    if os.path.isdir(lxcdir+i):
    		ct_list.append(i)
    except OSError: 
	ct_list = []
    return sorted(ct_list)


def listx():
    '''
    List all containers with status (Running, Frozen or Stopped) in a dict
    Same as lxc-list or lxc-ls --fancy (0.9)
    '''
    stopped = []
    frozen = []
    running = []

    for container in ls():
        state = info(container)['state']
        if state == 'RUNNING':
            running.append(container)
        elif state == 'FROZEN':
            frozen.append(container)
        elif state == 'STOPPED':
            stopped.append(container)

    return {'RUNNING': running,
            'FROZEN': frozen,
            'STOPPED': stopped}


def running():
    return listx()['RUNNING']


def frozen():
    return listx()['FROZEN']


def stopped():
    return listx()['STOPPED']


def start(container):
    '''
    Starts a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exists!'.format(container))
    if container in running(): raise ContainerAlreadyRunning('Container {} is already running!'.format(container))
    return _run('lxc-start -dn {}'.format(container))


def stop(container):
    '''
    Stops a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exists!'.format(container))
    if container in stopped(): raise ContainerNotRunning('Container {} is not running!'.format(container))
    return _run('lxc-stop -n {}'.format(container))


def freeze(container):
    '''
    Freezes a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exists!'.format(container))
    if not container in running(): raise ContainerNotRunning('Container {} is not running!'.format(container))
    return _run('lxc-freeze -n {}'.format(container))


def unfreeze(container):
    '''
    Unfreezes a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exists!'.format(container))
    if not container in frozen(): raise ContainerNotRunning('Container {} is not frozen!'.format(container))
    return _run('lxc-unfreeze -n {}'.format(container))


def destroy(container):
    '''
    Destroys a container
    '''
    if not exists(container): raise ContainerDoesntExists('Container {} does not exists!'.format(container))
    return _run('lxc-destroy -n {}'.format(container))


def checkconfig():
    '''
    Returns the output of lxc-checkconfig (colors cleared)
    '''
    out = _run('lxc-checkconfig', output=True)
    if out: return out.replace('[1;32m', '').replace('[1;33m', '').replace('[0;39m', '').replace('[1;32m', '').replace('\x1b', '').replace(': ', ':').split('\n')
    return out

def cgroup(container, key, value):
    if not exists(container): raise ContainerDoesntExists('Container {} does not exist!'.format(container))
    return _run('lxc-cgroup -n {} {} {}'.format(container, key, value))

def backup(container, sr_type='local', destination='/var/lxc-backup/'):
    '''
    Backup container with tar to a storage repository (SR). E.g: localy or with nfs
    If SR is localy then the path is /var/lxc-backup/
    otherwise if SR is NFS type then we just check if the SR is mounted in host side in /mnt/lxc-backup
    '''
    prefix = time.strftime("%Y-%m-%d__%H-%m.tar.gz")
    filename = '{}/{}-{}'.format(destination, container, prefix)
    was_running = False

    if not exists(container): raise ContainerDoesntExists('Container {} does not exist!'.format(container))
    if sr_type == 'local':
    	if not os.path.isdir(destination): raise DirectoryDoesntExists('Directory {} does not exist !'.format(destination))
    if sr_type == 'nfs':
        if not os.path.ismount(destination): raise NFSDirectoryNotMounted('NFS {} is not mounted !'.format(destination))

    if info(container)['state'] == 'RUNNING':
        was_running = True
        freeze(container)

    create_backup  = _run('tar czf {} -C /var/lib/lxc {}'.format(filename, container))

    if was_running == True:
        unfreeze(container)

    return create_backup
