#  Copyright © 2017 Yigit Dallilar <yigit.dallilar@gmail.com>
#
#  kernel.py is a part of pyakm. 
#
#  pyakm is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  pyakm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  The following additional terms are in effect as per Section 7 of the license:
#
#  The preservation of all legal notices and author attributions in
#  the material or in the Appropriate Legal Notices displayed
#  by works containing it is required.
#
#  You should have received a copy of the GNU General Public License
#  along with pyakm; If not, see <http://www.gnu.org/licenses/>.

import pyakm.pyalpm as alpm
import pyakm.alpminit as config
import requests, re, os, functools, dbus, time, sys
from bs4 import BeautifulSoup


conf = config.PacmanConfig(conf="/etc/pacman.conf")
handle = conf.initialize_alpm()

official_dict = {'linux':'core', 'linux-lts':'core',
                 'linux-zen':'extra'} #, 'linux-hardened':'extra'}

archive_url = "https://archive.archlinux.org/packages/"
aur_url = "https://aur.archlinux.org/rpc/?v=5&"

pkg_str = '%s-%s-x86_64.pkg.tar.xz'

cache_dir = '/var/cache/pyakm/'

class OfficialKernel:

    def __init__(self, kernel_name):

        self.type = "Official"
        self.kernel_name = kernel_name
        self.header_name = kernel_name + "-headers"
        self.repo = None
        self.local = None
        self.header = None
        self.vers = []
        self.uptodate = -1 # -1: not installed, 0:false, 1:true
        self.status = "Idle"
        self.task_name = None

    def Refresh(self, info_func=None):

        self.getKernelPackage(info_func=info_func)
        self.getHeaderPackage(info_func=info_func)
        self.getRepoKernel(info_func=info_func)
        self.getArchiveList(info_func=info_func)
        self._isUptoDate()

    def getKernelPackage(self, info_func=None):

        if info_func is not None:
            info_func('Checking local database for, ' + self.kernel_name)
        print('%s : Checking local database\n' % self.kernel_name, flush=True)

        db = handle.get_localdb()
        pkg = db.get_pkg(self.kernel_name)
        self.local = pkg

    def getHeaderPackage(self, info_func=None):

        if info_func is not None:
            info_func('Checking local database for, ' + self.header_name)
        print('%s : Checking local database\n' % self.header_name, flush=True)

        db = handle.get_localdb()
        pkg = db.get_pkg(self.header_name)
        self.header = pkg


    def getRepoKernel(self, opt=True, info_func=None):

        if info_func is not None:
            info_func('Obtain repo package, '+ self.kernel_name)
        print('%s : Obtaining repo package\n' % self.kernel_name, flush=True)
            
        dbs = handle.get_syncdbs()
        for db in dbs:
            if db.name == official_dict[self.kernel_name]:
                while(True):
                    try:
                        self.repo = db.get_pkg(self.kernel_name)
                        break
                    except:
                        info_func('%s : Failed retreive package %s. Retrying.' % \
                              self.kernel_name, self.kernel_name)
                        print('%s : Failed retreive package %s. Retrying.\n' % \
                              self.kernel_name, self.kernel_name, flush=True)
                        time.sleep(5)

    def getRepoHeader(self, opt=True, info_func=None):

        if info_func is not None:
            info_func('Obtain repo package, ', self.header_name)
        print('%s : Obtaining repo package\n' % self.header_name, flush=True)
            
        dbs = handle.get_syncdbs()
        for db in dbs:
            if db.name == official_dict[self.kernel_name]:
                while(True):
                    try:
                        return db.get_pkg(self.header_name)
                    except:
                        info_func('Failed retreive package %s. Retrying.' % \
                              self.kernel_name, self.header_name)
                        print('%s : Failed retreive package %s. Retrying.\n' % \
                              self.kernel_name, self.header_name, flush=True)
                        time.sleep(5)

            
    def getArchiveList(self, info_func=None):

        if info_func is not None:
            info_func('Retrieving archive list for, %s' % self.kernel_name)
        print('%s : Retrieving archive list\n' % self.kernel_name, flush=True)
        
        file_list = []
        vers = []
        url = archive_url + '/' + self.kernel_name[0] + '/' + self.kernel_name + '/'

        while(True):
            
            try:
                req = requests.get(url, timeout=6)
                soup = BeautifulSoup(req.text, 'html.parser')
                for a in soup.find_all('a'):
                    if (a['href'].split('.')[-1] == 'xz') & (a['href'].find('x86_64') > -1):
                        file_list.append(a['href'])

                for package in file_list:
                    vers.append(self._getVersFromFilename(package))

                self.vers = sorted(vers,
                                   key=functools.cmp_to_key(alpm.vercmp), reverse=True)
                break
            except:
                info_func('Failed retreive archive list. Retrying.')
                print('%s : Failed retreive archive list. Retrying.\n' % \
                      self.kernel_name, flush=True)
                time.sleep(5)
                continue

                
    def downloadKernel(self, version, opt=True, info_func=None):
        #1 : for kernel
        #0 : for header
        
        if opt:
            name = self.kernel_name
        else:
            name = self.header_name
            
        url = archive_url + '/' + name[0] + '/' + name + '/'
        package = pkg_str % (name, version)

        print('%s : Downloading %s\n' % (name, package), flush=True)
        
        attempt = 1
        while(True):
            
            try:
                req = requests.get(url+package, stream=True, timeout=6)
                print('%s : Connected to %s\n' % (name, archive_url), flush=True)
            except:
                print('%s : Failed to connect %s. Attempt [%02d]\n' % (name, archive_url, attempt),
                      flush=True)
                self.info_func('Failed to connect to archive server. Attempt [%02d]' % \
                               (attempt))
                attempt += 1
                time.sleep(5)
                continue

            try:
                tot = int(req.headers['Content-length'])
                chunk_sz = 4096
                f = open(cache_dir+package, 'wb')
            
                if info_func is not None: 
                    chnks = 0
                    for data in req.iter_content(chunk_size=chunk_sz):
                        chnks += 1
                        info_func("Downloading %s %3d%%" % (package,int(chnks*chunk_sz/tot*100)))
                        f.write(data)
                else:
                    for data in req.iter_content(chunk_size=chunk_sz):
                        f.write(data)

                f.close()

                req.close()
                break
            
            except:
                self.info_func('Failed to finish download. Retrying')
                print('%s : Failed to finish download.\n' % (name), flush=True)
                print('%s : Reconnecting to %s in 5 secs.\n' % (name, archive_url), flush=True)
                time.sleep(5)
                continue
                
    def upgradeKernel(self, opt=True, info_func=None):
        #1 : for kernel
        #0 : for header

        self.info_func = info_func
        self.task_name = 'Installing ' 
        
        if opt:
            if info_func is not None:
                handle.dlcb = self._dlcb
                handle.eventcb = self._eventcb
                handle.progresscb = self._progcb
                info_func('Upgrading, %s' % (self.kernel_name))
                print("%s : Upgrading\n" % (self.kernel_name), flush=True)
        else:
            if info_func is not None:
                handle.dlcb = self._dlcb
                handle.eventcb = self._eventcb
                handle.progresscb = self._progcb
                info_func('Upgrading, %s' % (self.header_name))
                print("%s : Upgrading\n" % (self.header_name), flush=True)
        
        self.check_lockfile(info_func=info_func)

        trans = handle.init_transaction()

        if opt:
            trans.add_pkg(self.repo)
        else:
            trans.add_pkg(self.getRepoHeader())

        self.do_transaction(trans)
            
        self.removeIgnorePkg(opt=opt, info_func=info_func)
        if opt:
            self.getKernelPackage(info_func=info_func)
        else:
            self.getHeaderPackage(info_func=info_func)

        if opt:
            if not self._isHeaderUpdated():
                self.upgradeKernel(False, info_func=info_func)

    def downgradeKernel(self, version, opt=True, info_func=None):
        #1 : for kernel
        #0 : for header

        self.task_name = 'Installing ' 
        
        if not any(version == item for item in self.vers):
            print('%s : unknown version (%s)\n' % (self.kernel_name, version), flush=True)
            return False

        self.info_func = info_func
        
        if opt:
            handle.dlcb = self._dlcb
            handle.eventcb = self._eventcb
            handle.progresscb = self._progcb
            name = self.kernel_name
        else:
            handle.dlcb = self._dlcb
            handle.eventcb = self._eventcb
            handle.progresscb = self._progcb
            name = self.header_name

        if info_func is not None: info_func('Downgrading, %s' % (name))
        print('%s : Downgrading.\n' % (name), flush=True)

        if not os.path.isfile(handle.cachedirs[0] + pkg_str % (name, version)):
            self.downloadKernel(version, opt, info_func=info_func)
            pkg = handle.load_pkg(cache_dir + pkg_str % \
                                  (name, version))
        else:
            print("%s : File found in %s.\n" % (name, handle.cachedirs[0]), flush=True)
            pkg = handle.load_pkg(handle.cachedirs[0] + pkg_str % (name, version))
        
        self.check_lockfile(info_func=info_func)

        trans = handle.init_transaction()
        trans.add_pkg(pkg)

        self.do_transaction(trans)

        self.addIgnorePkg(opt=opt, info_func=info_func)
        if opt:
            self.getKernelPackage(info_func=info_func)
        else:
            self.getHeaderPackage(info_func=info_func)

        if opt:
            if not self._isHeaderUpdated(info_func=info_func):
                self.downgradeKernel(version, False, info_func=info_func)

        return True

    def addIgnorePkg(self, opt=True, info_func=None):
        #1 : for kernel
        #0 : for header

        if opt:
            name = self.kernel_name
        else:
            name = self.header_name
            
        for ignored in handle.ignorepkgs:
            if ignored == name:
                if info_func is not None: info_func('%s is already in IgnorePkg' % name)
                return False

        if info_func is not None: info_func('Adding %s to IgnorePkg' % name)
        print('%s : Adding to IgnorePkg\n' % name, flush=True)
        
        lines = open('/etc/pacman.conf', 'r').readlines()
        
        for i in range(len(lines)):
            line = lines[i].split(' ')
            if (line[0] == "#IgnorePkg") | (line[0] == "IgnorePkg"):
                tmp = ["IgnorePkg", "="] + handle.ignorepkgs + \
                                       [name + "\n"]
                lines[i] = " ".join(tmp)

        lines = "".join(lines)

        f = open('/etc/pacman.conf', 'w')
        f.write(lines)
        handle.add_ignorepkg(name)

        f.close()

    def removeIgnorePkg(self, opt=True, info_func=None):
        #1 : for kernel
        #0 : for header
        if opt:
            name = self.kernel_name
        else:
            name = self.header_name

        print('%s : Removing IgnorePkg\n' % name, flush=True)
        
        for ignored in handle.ignorepkgs:
            if ignored == name:
                if info_func is not None: info_func('Removing %s from IgnorePkg' % name)
                
                lines = open('/etc/pacman.conf', 'r').readlines()
        
                for i in range(len(lines)):
                    line = lines[i].split(' ')
                    if (line[0] == "#IgnorePkg") | (line[0] == "IgnorePkg"):
                        tmp = ["IgnorePkg", "="] + handle.ignorepkgs + \
                                       ["\n"]
                        lines[i] = " ".join(tmp)

                lines = "".join(lines)

                f = open('/etc/pacman.conf', 'w')
                f.write(lines)
                handle.remove_ignorepkg(name)
                f.close()


    def removeKernel(self, opt=True, info_func=None):
        
        self.info_func = info_func
        self.task_name = 'Removing ' 
        
        if opt:
            if info_func is not None:
                handle.dlcb = self._dlcb
                handle.eventcb = self._eventcb
                handle.progresscb = self._progcb
                info_func('Removing, %s' % (self.kernel_name))
                print("%s : Removing\n" % self.kernel_name, flush=True)
        else:
            if info_func is not None:
                handle.dlcb = self._dlcb
                handle.eventcb = self._eventcb
                handle.progresscb = self._progcb
                info_func('Removing, %s' % (self.header_name))
                print("%s : Removing\n" % self.header_name, flush=True)

        self.check_lockfile(info_func=info_func)

        trans = handle.init_transaction()

        if opt:
            if self.local is None:
                return False
            trans.remove_pkg(self.local)
        else:
            trans.remove_pkg(self.header)

        self.do_transaction(trans)

        self.removeIgnorePkg(opt=opt, info_func=info_func)
        if opt:
            self.getKernelPackage(info_func=info_func)
            if self.header is not None:
                self.removeKernel(False, info_func=info_func)
        else:
            self.getHeaderPackage(info_func=info_func)

    def check_lockfile(self, info_func=None):

        cnt = 1
        while(True):
            if not os.path.isfile(handle.lockfile):
                break
            if info_func is not None: info_func('Waiting for other package manager to quit...')
            print('%s : Waiting for other package manager to quit. Attempt [%02d]\n' % \
                  (self.kernel_name, cnt), flush=True)
            time.sleep(5)
            cnt += 1

    def do_transaction(self, transaction):

        print("%s : Start transaction\n" % self.kernel_name, flush=True)
        while(True):
            try:
                transaction.prepare()
                transaction.commit()
                transaction.release()
                print("%s : Transcation finished\n" % self.kernel_name, flush=True)
                return True
            except:
                transaction.release()
                print("%s : Failed to complete transaction\n" % self.kernel_name, flush=True)
        
    def raiseNetworkError(self):
        raise networkError()
        
    def _isUptoDate(self):
		if self.local is None:
            return -1
#       elif self.kernel_name is "hardened"
#			get
		elif self.local.version != self.repo.version:
            return 0
        else:
            return 1
        
    
    def _isHeaderUpdated(self, info_func=None):
        if self.header is None:
            if info_func is not None: info_func(self.header_name + ' is not installed.')
            return False
        elif self.header.version != self.local.version:
            if info_func is not None: info_func(self.header_name + 'requires upgrade. (%s => %s)' % \
                  (self.header.version, self.local.version))
            return False
        else:
            if info_func is not None: info_func(self.header_name + ' is up to date.')
            return True
        
    def _getVersFromFilename(self, f_name):
        res = re.match(pkg_str % (self.kernel_name, "(\S+)"), f_name)
        return res.group(1)

    def _dlcb(self, f_name, down, tot):
        self.info_func("Downloading %s %3d%%" % (f_name, int(down/tot*100)))

    def _eventcb(self, *args):
        print('Event: ', args, flush=True)

    def _progcb(self, target, percent, n, i):
        self.info_func("%s %s %3d%%" % (self.task_name, target, percent) )


'''
class AURKernel:
    
    def __init__(self, kernel_name):
            
        self.type = "AUR"
        self.kernel_name = kernel_name
        self.repo = None
        self.local = None
        
        self.getLocalPackage()
        self.getRepoPackage()

    def getLocalPackage(self):
        
        db = handle.get_localdb()
        pkg = db.get_pkg(self.kernel_name)
        if pkg != None:
            self.local = pkg

    def getRepoPackage(self):

        info = requests.get(aur_url + "type=info&arg[]=%s" % self.kernel_name).json()
        if info['resultcount'] == 1:
            self.fillPkgInfo(info)

    def fillPkgInfo(self, info):
        
        tmp_info = info['results'][0]
        self.repo.name = tmp_info['Name']
        self.repo.version = tmp_info['Version']
        self.repo.desc = tmp_info['Description']
        self.repo.licences = tmp_info['Licenses']
        
    def upgradeKernel():
        pass

    def removeKernel(self):
        pass

    def setDefault():
        pass
'''
