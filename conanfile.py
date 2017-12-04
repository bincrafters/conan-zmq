#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, tools
import os


class ZMQConan(ConanFile):
    name = "zmq"
    version = "4.2.2"
    url = "https://github.com/bincrafters/conan-zmq"
    description = "ZeroMQ is a community of projects focused on decentralized messaging and computing"
    license = "https://github.com/someauthor/somelib/blob/master/LICENSES"
    exports_sources = ["LICENSE"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def system_requirements(self):
        if self.settings.os == "Linux":
            if tools.os_info.linux_distro == "ubuntu" or tools.os_info.linux_distro == "debian":
                arch = ''
                if self.settings.arch == "x86" and tools.detected_architecture() == "x86_64":
                    arch = ':i386'
                installer = tools.SystemPackageTool()
                installer.install('pkg-config%s' % arch)

    def source(self):
        extracted_dir = "zeromq-%s" % self.version
        if self.settings.os == "Windows":
            archive_name = "%s.tar.gz" % extracted_dir
        else:
            archive_name = "%s.zip" % extracted_dir
        source_url = "https://github.com/zeromq/libzmq/releases/download/v%s/%s" % (self.version, archive_name)
        tools.get(source_url)
        os.rename(extracted_dir, "sources")

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self.build_vs()
        else:
            self.build_configure()

    def build_vs(self):
        vs_version = int(str(self.settings.compiler.version))
        toolset = None
        if vs_version == 9:
            folder = 'vs2008'
        elif vs_version == 10:
            folder = 'vs2010'
        elif vs_version == 11:
            folder = 'vs2012'
        elif vs_version == 12:
            folder = 'vs2013'
        elif vs_version == 14:
            folder = 'vs2015'
        elif vs_version > 14:
            folder = 'vs2015'
            toolset = 'v141'
        if self.settings.build_type == 'Debug':
            config = 'DynDebug' if self.options.shared else 'StaticDebug'
        elif self.settings.build_type == 'Release':
            config = 'DynRelease' if self.options.shared else 'StaticRelease'
        with tools.chdir(os.path.join('sources', 'builds', 'msvc', folder)):
            command = tools.msvc_build_command(self.settings, 'libzmq.sln', upgrade_project=False,
                                               build_type=config, targets=['libzmq'], toolset=toolset)
            if self.settings.arch == 'x86':
                command = command.replace('/p:Platform="x86"', '/p:Platform="Win32"')
            self.run(command)

    def build_configure(self):
        with tools.chdir("sources"):
            for name in ['autogen.sh', 'configure', 'version.sh', os.path.join('config', 'install-sh')]:
                os.chmod(name, os.stat(name).st_mode | 0o111)

            self.run('./autogen.sh')

            env_build = AutoToolsBuildEnvironment(self)
            args = ['--prefix=%s' % self.package_folder,
                    '--with-pic',
                    '--without-docs']
            if self.options.shared:
                args.extend(['--disable-static', '--enable-shared'])
            else:
                args.extend(['--enable-static', '--disable-shared'])
            if self.settings.build_type == 'Debug':
                args.append('--enable-debug')
            env_build.configure(args=args)
            env_build.make()
            env_build.make(args=['install'])

    def package(self):
        with tools.chdir("sources"):
            self.copy(pattern="LICENSE")
        if self.settings.compiler == 'Visual Studio':
            kind = 'dynamic' if self.options.shared else 'static'
            if self.settings.arch == 'x86':
                arch = 'Win32'
            elif self.settings.arch == 'x86_64':
                arch = 'x64'
            vs_version = {8: 'v80',
                          9: 'v90',
                          10: 'v100',
                          11: 'v110',
                          12: 'v120',
                          14: 'v140',
                          15: 'v141'}.get(int(str(self.settings.compiler.version)))
            libdir = os.path.join('sources', 'bin', arch, str(self.settings.build_type), vs_version, kind)
            self.copy(pattern='*.lib', src=libdir, dst='lib', keep_path=False)
            self.copy(pattern='*.dll', src=libdir, dst='bin', keep_path=False)
            self.copy(pattern='*.h', src=os.path.join('sources', 'include'), dst='include', keep_path=True)

    def package_info(self):
        if self.settings.compiler == 'Visual Studio':
            self.cpp_info.libs = ['libzmq', 'ws2_32', 'Iphlpapi']
            if not self.options.shared:
                self.cpp_info.defines.append('ZMQ_STATIC')
        else:
            self.cpp_info.libs = ['zmq']
        if self.settings.os == "Linux":
            self.cpp_info.libs.append('pthread')
