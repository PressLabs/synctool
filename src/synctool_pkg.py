#! /usr/bin/python2.7
#
#	synctool_pkg.py		WJ111
#
#   synctool by Walter de Jong <walter@heiho.net> (c) 2003-2013
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

import synctool_config
import synctool_param
import synctool_stat
import synctool_lib

from synctool_lib import verbose,stdout,stderr,terse,unix_out,dryrun_msg

import os
import sys
import string
import getopt
import errno

# enums for command-line options
ACTION_INSTALL = 1
ACTION_REMOVE = 2
ACTION_LIST = 3
ACTION_UPDATE = 4
ACTION_UPGRADE = 5
ACTION_CLEAN = 6

# action to perform
ACTION = 0

# list of packages given on the command-line
PKG_LIST = None

# list of Linux package managers: (Linux release file, package manager)
LINUX_PACKAGE_MANAGERS = (
	( '/etc/debian_version', 'apt-get' ),
	( '/etc/SuSE-release', 'zypper' ),
	( '/etc/redhat-release', 'yum' ),
	( '/etc/arch-release', 'pacman' ),
	( '/etc/gentoo-release', 'portage' ),
	( '/etc/slackware-version', 'swaret' ),
	( '/etc/fedora-release', 'yum' ),
	( '/etc/yellowdog-release', 'yum' ),
	( '/etc/mandrake-release', 'urpmi' ),
)


def package_manager():
	'''return instance of SyncPkg installer class'''

	detected = False

	if not synctool_param.PACKAGE_MANAGER:
		detect_installer()

		if not synctool_param.PACKAGE_MANAGER:
			stderr('failed to detect package management system')
			stderr('please configure it in synctool.conf')
			sys.exit(1)

		detected = True

	for mgr in synctool_param.KNOWN_PACKAGE_MANAGERS:
		if synctool_param.PACKAGE_MANAGER == mgr:
			short_mgr = string.replace(mgr, '-', '')

			# load the module
			module = __import__('synctool_pkg_%s' % short_mgr)

			# find the package manager class
			pkgclass = getattr(module, 'SyncPkg%s' % string.capitalize(short_mgr))

			# instantiate the class
			return pkgclass()

	if detected:
		stderr('package manager %s is not supported yet' % synctool_param.PACKAGE_MANAGER)
	else:
		stderr("unknown package manager defined: '%s'" % synctool_param.PACKAGE_MANAGER)

	sys.exit(1)


def detect_installer():
	'''Attempt to detect the operating system and package system
	Returns instance of a SyncPkg installer class'''

	#
	# attempt a best effort at detecting OSes for the purpose of
	# choosing a package manager
	# It's probably not 100% fool-proof, but as said, it's a best effort
	#
	# Problems:
	# - there are too many platforms and too many Linux distros
	# - there are too many different packaging systems
	# - there are RedHat variants that all have /etc/redhat-release but
	#   use different package managers
	# - SuSE has three (!) package managers that are all in use
	#   and it seems to be by design (!?)
	# - I've seen apt-get work with dpkg, and I've seen apt-get work with rpm
	# - MacOS X has no 'standard' software packaging (the App store??)
	#   There are ports, fink, brew. I prefer 'brew'
	# - The *BSDs have both pkg_add and ports
	# - FreeBSD has freebsd-update to upgrade packages
	#

	platform = os.uname()[0]

	if platform == 'Linux':
		verbose('detected platform Linux')

		stat = synctool_stat.SyncStat()

		# use release file to detect Linux distro,
		# and choose package manager based on that

		for (release_file, pkgmgr) in LINUX_PACKAGE_MANAGERS:
			stat.stat(release_file)
			if stat.exists():
				verbose('detected %s' % release_file)
				verbose('choosing package manager %s' % pkgmgr)
				synctool_param.PACKAGE_MANAGER = pkgmgr
				return

		stderr('unknown Linux distribution')

	elif platform == 'Darwin':			# assume MacOS X
		verbose('detected platform MacOS X')
		# some people like port
		# some people like fink
		# I like homebrew
		verbose('choosing package manager brew')
		synctool_param.PACKAGE_MANAGER = 'brew'

	elif platform in ('NetBSD', 'OpenBSD', 'FreeBSD'):
		verbose('detected platform %s' % platform)

		# choose bsdpkg
		# I know there are ports, but you can 'make' those easily in *BSD
		# or maybe ports will be a seperate module in the future

		verbose('choosing package manager bsdpkg')
		synctool_param.PACKAGE_MANAGER = 'bsdpkg'

	# platforms that are not supported yet, but I would like to support
	# or well, most of them
	# Want to know more OSes? See the source of autoconf's config.guess

	elif platform in ('4.4BSD', '4.3bsd', 'BSD/OS', 'SunOS', 'AIX', 'OSF1',
		'HP-UX', 'HI-UX', 'IRIX', 'UNICOS', 'UNICOS/mp', 'ConvexOS', 'Minix',
		'Windows_95', 'Windows_NT', 'CYGWIN', 'MinGW',
		'LynxOS', 'UNIX_System_V', 'BeOS', 'TOPS-10', 'TOPS-20'):
		verbose('detected platform %s' % platform)
		stderr('synctool package management under %s is not yet supported' % platform)

	else:
		stderr("unknown platform '%s'" % platform)


def there_can_be_only_one():
	print 'Specify only one of these options:'
	print '  -l, --list   [PACKAGE ...]     List installed packages'
	print '  -i, --install PACKAGE [..]     Install package'
	print '  -R, --remove  PACKAGE [..]     Uninstall package'
	print '  -u, --update                   Update the database of available packages'
	print '  -U, --upgrade                  Upgrade all outdated packages'
	print '  -C, --clean                    Cleanup caches of downloaded packages'
	print
	sys.exit(1)


def usage():
	print 'usage: %s [options] [package list]' % os.path.basename(sys.argv[0])
	print 'options:'
	print '  -h, --help                     Display this information'
	print '  -c, --conf=dir/file            Use this config file'
	print '                                 (default: %s)' % synctool_param.DEFAULT_CONF
	print '  -l, --list   [PACKAGE ...]     List installed packages'
	print '  -i, --install PACKAGE [..]     Install package'
	print '  -R, --remove  PACKAGE [..]     Uninstall package'
	print '  -u, --update                   Update the database of available packages'
	print '  -U, --upgrade                  Upgrade all outdated packages'
	print '  -C, --clean                    Cleanup caches of downloaded packages'
	print
	print '  -f, --fix                      Perform upgrade (otherwise, do dry-run)'
	print '  -v, --verbose                  Be verbose'
	print '      --unix                     Output actions as unix shell commands'
	print '  -m, --manager PACKAGE_MANAGER  (Force) select this package manager'
	print
	print 'Supported package managers are:'

	# print list of supported package managers
	# format it at 78 characters wide
	print ' ',
	n = 2
	for pkg in synctool_param.KNOWN_PACKAGE_MANAGERS:
		if n + len(pkg) + 1 <= 78:
			n = n + len(pkg) + 1
			print pkg,
		else:
			n = 2 + len(pkg) + 1
			print
			print ' ', pkg,

	print
	print
	print 'The package list must be given last'
	print 'Note that --upgrade does a dry run unless you specify --fix'
	print
	print 'synctool-pkg by Walter de Jong <walter@heiho.net> (c) 2013'


def get_options():
	global ACTION, PKG_LIST

	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)

	synctool_lib.DRY_RUN = True				# set default dry-run

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hc:iRluUCm:fvq',
			['help', 'conf=',
			'list', 'install', 'remove', 'update', 'upgrade', 'clean',
			'cleanup', 'manager=',
			'fix', 'verbose', 'unix', 'quiet'])
	except getopt.error, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except getopt.GetoptError, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except:
		usage()
		sys.exit(1)

	# first read the config file
	for opt, arg in opts:
		if opt in ('-h', '--help', '-?'):
			usage()
			sys.exit(1)

		if opt in ('-c', '--conf'):
			synctool_param.CONF_FILE = arg
			continue

	synctool_config.read_config()

	# then process the other options
	ACTION = 0
	PKG_LIST = []

	for opt, arg in opts:
		if opt in ('-h', '--help', '-?', '-c', '--conf'):
			# already done
			continue

		if opt in ('-i', '--install'):
			if ACTION > 0 and ACTION != ACTION_INSTALL:
				there_can_be_only_one()

			ACTION = ACTION_INSTALL
			continue

		if opt in ('-R', '--remove'):
			if ACTION > 0 and ACTION != ACTION_REMOVE:
				there_can_be_only_one()

			ACTION = ACTION_REMOVE
			continue

		if opt in ('-l', '--list'):
			if ACTION > 0 and ACTION != ACTION_LIST:
				there_can_be_only_one()

			ACTION = ACTION_LIST
			continue

		if opt in ('-u', '--update'):
			if ACTION > 0 and ACTION != ACTION_UPDATE:
				there_can_be_only_one()

			ACTION = ACTION_UPDATE
			continue

		if opt in ('-U', '--upgrade'):
			if ACTION > 0 and ACTION != ACTION_UPGRADE:
				there_can_be_only_one()

			ACTION = ACTION_UPGRADE
			continue

		if opt in ('-C', '--clean', '--cleanup'):
			if ACTION > 0 and ACTION != ACTION_CLEAN:
				there_can_be_only_one()

			ACTION = ACTION_CLEAN
			continue

		if opt in ('-m', '--manager'):
			if not arg in synctool_param.KNOWN_PACKAGE_MANAGERS:
				stderr("error: unknown or unsupported package manager '%s'" % arg)
				sys.exit(1)

			synctool_param.PACKAGE_MANAGER = arg
			continue

		if opt in ('-f', '--fix'):
			synctool_lib.DRY_RUN = False
			continue

		if opt in ('-v', '--verbose'):
			synctool_lib.VERBOSE = True
			continue

		if opt == '--unix':
			synctool_lib.UNIX_CMD = True
			continue

		if opt in ('-q', '--quiet'):
			# silently ignore this option
			continue

	if not ACTION:
		usage()
		sys.exit(1)

	if ACTION in (ACTION_LIST, ACTION_INSTALL, ACTION_REMOVE):
		PKG_LIST = args

		if ACTION in (ACTION_INSTALL, ACTION_REMOVE) and (args == None or not len(args)):
			stderr('error: options --install and --remove require a package name')
			sys.exit(1)

	elif args != None and len(args) > 0:
		stderr('error: excessive arguments on command line')
		sys.exit(1)

	#
	# disable dry-run unless --upgrade was given
	# a normal --upgrade will do a dry-run and show what upgrades are available
	# --upgrade -f will do the upgrade
	#
	# The other actions will execute immediatly
	#
	if ACTION != ACTION_UPGRADE:
		synctool_lib.DRY_RUN = False


def main():
	get_options()

	synctool_lib.QUIET = not synctool_lib.VERBOSE

	pkg = package_manager()

	if ACTION == ACTION_LIST:
		pkg.list(PKG_LIST)

	elif ACTION == ACTION_INSTALL:
		pkg.install(PKG_LIST)

	elif ACTION == ACTION_REMOVE:
		pkg.remove(PKG_LIST)

	elif ACTION == ACTION_UPDATE:
		pkg.update()

	elif ACTION == ACTION_UPGRADE:
		pkg.upgrade()

	elif ACTION == ACTION_CLEAN:
		pkg.clean()

	else:
		raise RuntimeError, 'BUG: unknown ACTION code %d' % ACTION


if __name__ == '__main__':
	try:
		main()
	except IOError, ioerr:
		if ioerr.errno == errno.EPIPE:		# Broken pipe
			pass
		else:
			print ioerr

	except KeyboardInterrupt:		# user pressed Ctrl-C
		pass


# EOB
