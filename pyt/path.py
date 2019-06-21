# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import re
import os
import unittest
import sys
import inspect
import importlib
import logging
import hashlib
import site

from .compat import *
from .utils import modname


logger = logging.getLogger(__name__)


class RerunFile(object):
    def __init__(self):
        import tempfile
        self.filepath = os.path.join(tempfile.gettempdir(), "{}.txt".format(modname()))

    def __enter__(self):
        self.fp = open(self.filepath, encoding="utf-8", mode="w+")
        return self

    def writeln(self, s):
        self.fp.write(s)
        self.fp.write("\n")

    def __exit__(self, exception_type, exception_value, traceback):
        self.fp.close()
        self.fp = None

    def read(self):
        with open(self.filepath, encoding="utf-8", mode="r+") as fp:
            return fp.read()

    def __iter__(self):
        with open(self.filepath, encoding="utf-8", mode="r+") as fp:
            for line in fp:
                yield line.strip()


class PathGuesser(object):
    """PathGuesser

    This class compiles the possible paths, it is created in the TestLoader and then 
    the .possible attribute is iterated to actually load the tests.

    The .possible property consists of PathFinder objects

    https://docs.python.org/3/library/unittest.html#test-discovery
    """
    def __init__(self, name, basedir="", method_prefix='test', **kwargs):
        self.name = name
        if not basedir:
            basedir = os.getcwd()
        self.basedir = basedir
        self.method_prefix = method_prefix
        self.set_possible()

    def raise_any_error(self):
        """raise any found error in the possible PathFinders"""
        for tc in self.possible:
            tc.raise_found_error()

    def set_possible(self):
        '''
        break up a module path to its various parts (prefix, module, class, method)

        this uses PEP 8 conventions, so foo.Bar would be foo module with class Bar

        return -- list -- a list of possible interpretations of the module path
            (eg, foo.bar can be bar module in foo module, or bar method in foo module)
        '''
        possible = []
        name = self.name
        logger.debug('Guessing test name: {}'.format(name))

        name_f = self.name.lower()
        filepath = ""
        if name_f.endswith(".py") or ".py:" in name_f:
            # path/something:Class.method
            bits = name.split(":", 1)
            filepath = bits[0]
            logger.debug('Found filepath: {}'.format(filepath))

            name = bits[1] if len(bits) > 1 else ""
            if name:
                logger.debug('Found test name: {} for filepath: {}'.format(name, filepath))

        bits = name.split('.')
        basedir = self.basedir
        method_prefix = self.method_prefix

        # check if the last bit is a Class
        if re.search(r'^\*?[A-Z]', bits[-1]):
            logger.debug('Found class in name: {}'.format(bits[-1]))
            possible.append(PathFinder(basedir, method_prefix, **{
                'class_name': bits[-1],
                'module_name': bits[-2] if len(bits) > 1 else '',
                'prefix': os.sep.join(bits[0:-2]),
                'filepath': filepath,
            }))
        elif len(bits) > 1 and re.search(r'^\*?[A-Z]', bits[-2]):
            logger.debug('Found class in name: {}'.format(bits[-2]))
            possible.append(PathFinder(basedir, method_prefix, **{
                'class_name': bits[-2],
                'method_name': bits[-1],
                'module_name': bits[-3] if len(bits) > 2 else '',
                'prefix': os.sep.join(bits[0:-3]),
                'filepath': filepath,
            }))
        else:
            if self.name:
                if filepath:
                    if len(bits):
                        possible.append(PathFinder(basedir, method_prefix, **{
                            'filepath': filepath,
                            'method_name': bits[0],
                        }))
                    else:
                        possible.append(PathFinder(basedir, method_prefix, **{
                            'filepath': filepath,
                        }))

                else:
                    logger.debug('Test name is ambiguous')
                    possible.append(PathFinder(basedir, method_prefix, **{
                        'module_name': bits[-1],
                        'prefix': os.sep.join(bits[0:-1]),
                        'filepath': filepath,
                    }))
                    possible.append(PathFinder(basedir, method_prefix, **{
                        'method_name': bits[-1],
                        'module_name': bits[-2] if len(bits) > 1 else '',
                        'prefix': os.sep.join(bits[0:-2]),
                        'filepath': filepath,
                    }))
                    possible.append(PathFinder(basedir, method_prefix, **{
                        'prefix': os.sep.join(bits),
                        'filepath': filepath,
                    }))

            else:
                possible.append(PathFinder(basedir, method_prefix, filepath=filepath))

        logger.debug("Found {} possible test names".format(len(possible)))
        self.possible = possible


class PathFinder(object):
    """Pathfinder class

    this is where all the magic happens, PathGuesser guesses on what the paths might
    be and creates instances of this class, those instances then actually validate
    the guesses and allow the tests to be loaded or not
    """
    def __init__(self, basedir, method_prefix='test', **kwargs):
        self.basedir = basedir
        self.method_prefix = method_prefix
        self.module_prefixes = ["test_", "test"]
        self.module_postfixes = ["_test", "test", "_tests", "tests"]
        for k, v in kwargs.items():
            setattr(self, k, v)

    def has_module(self):
        v = getattr(self, 'module_name', None)
        return bool(v)

    def has_class(self):
        v = getattr(self, 'class_name', None)
        return bool(v)

    def has_method(self):
        v = getattr(self, 'method_name', None)
        return bool(v)

    def __str__(self):
        ret = ''
        for k in ['prefix', 'module_name', 'class_name', 'method_name', 'filepath']:
            v = getattr(self, k, None)
            if v:
                ret += "{}: {}, ".format(k, v)

        return ret.rstrip(', ')

    def raise_found_error(self):
        """raise an error if one was found, otherwise do nothing"""
        error_info = getattr(self, 'error_info', None)
        if error_info:

            reraise(*error_info)

    def modules(self):
        """return modules that match module_name"""

        # since the module has to be importable we go ahead and put the
        # basepath as the very first path to check as that should minimize
        # namespace collisions, this is what unittest does also
        sys.path.insert(0, self.basedir)
        for p in self.paths():
            # http://stackoverflow.com/questions/67631/
            try:
                module_name = self.module_path(p)
                logger.debug("Importing {} from path {}".format(module_name, p))
                m = importlib.import_module(module_name)
                yield m

            except Exception as e:
                logger.warning('Caught exception while importing {}: {}'.format(p, e))
                logger.warning(e, exc_info=True)
                error_info = getattr(self, 'error_info', None)
                if not error_info:
                    exc_info = sys.exc_info()
                    #raise e.__class__, e, exc_info[2]
                    #self.error_info = (e, exc_info)
                    self.error_info = exc_info
                continue

        sys.path.pop(0)

    def classes(self):
        """the partial self.class_name will be used to find actual TestCase classes"""
        for module in self.modules():
            cs = inspect.getmembers(module, inspect.isclass)
            class_name = getattr(self, 'class_name', '')
            class_regex = ''
            if class_name:
                if class_name.startswith("*"):
                    class_name = class_name.strip("*")
                    class_regex = re.compile(r'.*?{}'.format(class_name), re.I)
                else:
                    class_regex = re.compile(r'^{}'.format(class_name), re.I)

            for c_name, c in cs:
                can_yield = True
                if class_regex and not class_regex.match(c_name):
                #if class_name and class_name not in c_name:
                    can_yield = False

                if can_yield and issubclass(c, unittest.TestCase):
                    if c is not unittest.TestCase: # ignore actual TestCase class
                        logger.debug('class: {} matches {}'.format(c_name, class_name))
                        yield c

    def method_names(self):
        """return the actual test methods that matched self.method_name"""
        for c in self.classes():
            #ms = inspect.getmembers(c, inspect.ismethod)
            # http://stackoverflow.com/questions/17019949/
            ms = inspect.getmembers(c, lambda f: inspect.ismethod(f) or inspect.isfunction(f))
            method_name = getattr(self, 'method_name', '')
            method_regex = ''
            if method_name:
                if method_name.startswith(self.method_prefix):
                    method_regex = re.compile(r'^{}'.format(method_name), flags=re.I)

                else:

                    if method_name.startswith("*"):
                        method_name = method_name.strip("*")
                        method_regex = re.compile(
                            r'^{}[_]{{0,1}}.*?{}'.format(self.method_prefix, method_name),
                            flags=re.I
                        )
                    else:
                        method_regex = re.compile(
                            r'^{}[_]{{0,1}}{}'.format(self.method_prefix, method_name),
                            flags=re.I
                        )

            for m_name, m in ms:
                if not m_name.startswith(self.method_prefix): continue

                can_yield = True
                if method_regex and not method_regex.match(m_name):
                    can_yield = False

                if can_yield:
                    logger.debug('method: {} matches {}'.format(m_name, method_name))
                    yield c, m_name

    def _find_basename(self, name, basenames, is_prefix=False):
        """check if name combined with test prefixes or postfixes is found anywhere
        in the list of basenames

        :param name: string, the name you're searching for
        :param basenames: list, a list of basenames to check
        :param is_prefix: bool, True if this is a prefix search, which means it will
            also check if name matches any of the basenames without the prefixes or
            postfixes, if it is False then the prefixes or postfixes must be present
            (ie, the module we're looking for is the actual test module, not the parent
             modules it's contained in)
        :returns: string, the basename if it is found
        """
        ret = ""
        fileroots = [(os.path.splitext(n)[0], n) for n in basenames]
        glob = False
        if name.startswith("*"):
            glob = True
        name = name.strip("*")

        for fileroot, basename in fileroots:
            if name in fileroot or fileroot in name:
                for pf in self.module_postfixes:
                    logger.debug(
                        'Checking if basename {} starts with {} and ends with {}'.format(
                        basename,
                        name,
                        pf
                    ))
                    if glob:
                        if name in fileroot and fileroot.endswith(pf):
                            ret = basename
                            break
                    else:
                        if fileroot.startswith(name) and fileroot.endswith(pf):
                            ret = basename
                            break

                if not ret:
                    for pf in self.module_prefixes:
                        n = pf + name
                        logger.debug('Checking if basename {} starts with {}'.format(basename, n))
                        if glob:
                            if fileroot.startswith(pf) and name in fileroot:
                                ret = basename
                                break
                        else:
                            if fileroot.startswith(n):
                                ret = basename
                                break

                if not ret:
                    if is_prefix:
                        logger.debug('Checking if basename {} starts with {}'.format(basename, name))
                        if basename.startswith(name) or (glob and name in basename):
                            ret = basename

                        else:
                            logger.debug(
                                'Checking if basename {} starts with {} and is a test module'.format(
                                basename,
                                name
                            ))
                            if glob:
                                if name in basename and self._is_module_path(basename):
                                    ret = basename

                            else:
                                if basename.startswith(name) and self._is_module_path(basename):
                                    ret = basename

                if ret:
                    logger.debug('Found basename {}'.format(ret))
                    break

        return ret

    def _find_prefix_paths(self, basedir, prefix):
        """the prefix is what comes before the module name (prefix.module_name) so this
        will only find prefixes, not modules"""
        ret = basedir
        modnames = re.split(r"[\.\/]", prefix)
        seen_paths = set()

        for root, dirs, files in self.walk(basedir):
            logger.debug("Checking {} for prefix {}".format(root, prefix))
            ret = root
            for modname in modnames:
                for root2, dirs2, files2 in self.walk(ret):
                    logger.debug("Checking {} for modname {}".format(root2, modname))
                    ret = ""
                    basename = self._find_basename(modname, dirs2, is_prefix=True)
                    if basename:
                        ret = os.path.join(root2, basename)
                        logger.debug("Found prefix path {}".format(ret))
                        break

                if not ret:
                    logger.debug("Could not find a prefix path in {} matching {}".format(root, modname))
                    break

            if ret:
                if ret not in seen_paths:
                    seen_paths.add(ret)
                    logger.debug("Yielding prefix path {}".format(ret))
                    yield ret

    def _find_prefix_path(self, basedir, prefix):
        """Similar to _find_prefix_paths() but only returns the first match"""
        ret = ""
        for ret in self._find_prefix_paths(basedir, prefix):
            break

        if not ret:
            raise IOError("Could not find prefix {} in path {}".format(prefix, basedir))

        return ret

    def _find_module_path(self, basedir, modname):
        """find a module matching modname in basedir and return the path to that module

        :param basedir: string, the base directory to look for the module in
        :param modname: string, the module name
        :returns: string, the full path to the found module, empty if nothing found
        """
        ret = ""

        logger.debug('Checking for a module that matches {} in {}'.format(modname, basedir))
        for root, dirs, files in self.walk(basedir):
            basename = self._find_basename(modname, files, is_prefix=False)
            if basename:
                ret = os.path.join(root, basename)
                break

            for basename in files:
                fileroot = os.path.splitext(basename)[0]
                if fileroot in modname or modname in fileroot:
                    for pf in self.module_postfixes:
                        n = modname + pf
                        logger.debug('Checking {} against {}'.format(n, fileroot))
                        if fileroot.startswith(n):
                            ret = os.path.join(root, basename)
                            break

                    if not ret:
                        for pf in self.module_prefixes:
                            n = pf + modname
                            logger.debug('Checking {} against {}'.format(n, fileroot))
                            if fileroot.startswith(n):
                                ret = os.path.join(root, basename)
                                break

                    if not ret:
                        if self._is_module_path(basename) and modname == basename:
                            ret = os.path.join(root, basename)
                            break

                if ret: break
            if ret: break

        if not ret:
            ret = self._find_prefix_path(basedir, modname)
            if not ret:
                raise IOError("Could not find a module path with {}".format(modname))

        logger.debug("Found module path {}".format(ret))
        return ret

    def DISABLED_find_module_path(self, basedir, modname):
        """find a module matching modname in basedir and return the path to that module

        :param basedir: string, the base directory to look for the module in
        :param modname: string, the module name
        :returns: string, the full path to the found module, empty if nothing found
        """
        ret = ""

        try:
            ret = self._find_prefix_path(basedir, modname)
            pout.v(ret)

        except IOError:
            logger.debug('Checking for a module that matches {} in {}'.format(modname, basedir))
            for root, dirs, files in self.walk(basedir):
                basename = self._find_basename(modname, files, is_prefix=False)
                if basename:
                    ret = os.path.join(root, basename)
                    break

                for basename in files:
                    fileroot = os.path.splitext(basename)[0]
                    if fileroot in modname or modname in fileroot:
                        for pf in self.module_postfixes:
                            n = modname + pf
                            logger.debug('Checking {} against {}'.format(n, fileroot))
                            if fileroot.startswith(n):
                                ret = os.path.join(root, basename)
                                break

                        if not ret:
                            for pf in self.module_prefixes:
                                n = pf + modname
                                logger.debug('Checking {} against {}'.format(n, fileroot))
                                if fileroot.startswith(n):
                                    ret = os.path.join(root, basename)
                                    break

                        if not ret:
                            if self._is_module_path(basename) and modname == basename:
                                ret = os.path.join(root, basename)
                                break

                    if ret: break
                if ret: break

        if not ret:
            raise IOError("Could not find a module path with {}".format(modname))

        logger.debug("Found module path {}".format(ret))
        return ret

    def _is_module_path(self, path):
        """Returns true if the passed in path is a test module path

        :param path: string, the path to check, will need to start or end with the
            module test prefixes or postfixes to be considered valid
        :returns: boolean, True if a test module path, False otherwise
        """
        ret = False
        basename = os.path.basename(path)
        fileroot = os.path.splitext(basename)[0]
        for pf in self.module_postfixes:
            if fileroot.endswith(pf):
                ret = True
                break

        if not ret:
            for pf in self.module_prefixes:
                if fileroot.startswith(pf):
                    ret = True
                    break
        return ret

    def walk(self, basedir):
        """Walk all the directories of basedir except hidden directories

        :param basedir: string, the directory to walk
        :returns: generator, same as os.walk
        """
        system_d = SitePackagesDir()
        filter_system_d = system_d and os.path.commonprefix([system_d, basedir]) != system_d

        for root, dirs, files in os.walk(basedir, topdown=True):
            # ignore dot directories and private directories (start with underscore)
            dirs[:] = [d for d in dirs if d[0] != '.' and d[0] != "_"]

            if filter_system_d:
                dirs[:] = [d for d in dirs if not d.startswith(system_d)]

            # filter out .pyc files
            files[:] = [f for f in files if not f.lower().endswith(".pyc")]

            yield root, dirs, files

    def paths(self):
        '''
        given a basedir, yield all test modules paths recursively found in
        basedir that are test modules

        return -- generator
        '''
        module_name = getattr(self, 'module_name', '')
        module_prefix = getattr(self, 'prefix', '')
        filepath = getattr(self, 'filepath', '')

        if filepath:
            if os.path.isabs(filepath):
                yield filepath

            else:
                yield os.path.join(self.basedir, filepath)

        else:
            if module_prefix:
                basedirs = self._find_prefix_paths(self.basedir, module_prefix)
            else:
                basedirs = [self.basedir]

            for basedir in basedirs:
                try:
                    if module_name:
                        path = self._find_module_path(basedir, module_name)

                    else:
                        path = basedir

                    if os.path.isfile(path):
                        logger.debug('Module path: {}'.format(path))
                        yield path

                    else:
                        seen_paths = set()
                        for root, dirs, files in self.walk(path):
                            for basename in files:
                                if basename.startswith("__init__"):
                                    if self._is_module_path(root):
                                        filepath = os.path.join(root, basename)
                                        if filepath not in seen_paths:
                                            logger.debug('Module package path: {}'.format(filepath))
                                            seen_paths.add(filepath)
                                            yield filepath

                                else:
                                    fileroot = os.path.splitext(basename)[0]
                                    for pf in self.module_postfixes:
                                        if fileroot.endswith(pf):
                                            filepath = os.path.join(root, basename)
                                            if filepath not in seen_paths:
                                                logger.debug('Module postfix path: {}'.format(filepath))
                                                seen_paths.add(filepath)
                                                yield filepath

                                    for pf in self.module_prefixes:
                                        if fileroot.startswith(pf):
                                            filepath = os.path.join(root, basename)
                                            if filepath not in seen_paths:
                                                logger.debug('Module prefix path: {}'.format(filepath))
                                                seen_paths.add(filepath)
                                                yield filepath

                except IOError as e:
                    # we failed to find a suitable path
                    logger.warning(e, exc_info=True)
                    pass

    def module_path(self, filepath):
        """given a filepath like /base/path/to/module.py this will convert it to
        path.to.module so it can be imported"""
        possible_modbits = re.split('[\\/]', filepath.strip('\\/'))
        basename = possible_modbits[-1]
        prefixes = possible_modbits[0:-1]
        modpath = []
        discarded = []

        # find the first directory that has an __init__.py
        for i in range(len(prefixes)):
            path_args = ["/"]
            path_args.extend(prefixes[0:i+1])
            path_args.append('__init__.py')
            prefix_module = os.path.join(*path_args)
            #logger.debug("Checking prefix modulepath: {}".format(prefix_module))
            if os.path.isfile(prefix_module):
                #logger.debug("Found start of modulepath: {}".format(prefixes[i]))
                modpath = prefixes[i:]
                break

            else:
                discarded = path_args[0:-1]

        modpath.append(basename)

        # convert the remaining file path to a python module path that can be imported
        module_name = '.'.join(modpath)
        module_name = re.sub(r'(?:\.__init__)?\.py$', '', module_name, flags=re.I)
        logger.debug("Module path {} found in filepath {}".format(module_name, filepath))
        return module_name


# !!! Ripped from pout.path
class SitePackagesDir(String):
    """Finds the site-packages directory and sets the value of this string to that
    path"""
    _basepath = ""
    def __new__(cls):
        basepath = cls._basepath
        if not basepath:
            try:
                paths = site.getsitepackages()
                basepath = paths[0] 
                logger.debug(
                    "Found site-packages directory {} using site.getsitepackages".format(
                        basepath
                    )
                )

            except AttributeError:
                # we are probably running this in a virtualenv, so let's try a different
                # approach
                # try and brute-force discover it since it's not defined where it
                # should be defined
                sitepath = os.path.join(os.path.dirname(site.__file__), "site-packages")
                if os.path.isdir(sitepath):
                    basepath = sitepath
                    logger.debug(
                        "Found site-packages directory {} using site.__file__".format(
                            basepath
                        )
                    )

                else:
                    for path in sys.path:
                        if path.endswith("site-packages"):
                            basepath = path
                            logger.debug(
                                "Found site-packages directory {} using sys.path".format(
                                    basepath
                                )
                            )
                            break

                    if not basepath:
                        for path in sys.path:
                            if path.endswith("dist-packages"):
                                basepath = path
                                logger.debug(
                                    "Found dist-packages directory {} using sys.path".format(
                                        basepath
                                    )
                                )
                                break

        if not basepath:
            raise IOError("Could not find site-packages directory")

        cls._basepath = basepath

        return super(SitePackagesDir, cls).__new__(cls, basepath)

