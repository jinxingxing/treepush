#!/usr/bin/env python2
# coding: utf8

__author__ = 'JinXing'
__VERSION__ = 0.2

import sys
from sourcepool import SourcePool
from manager import TPushManager
from helper import *


def _get_format_dict(format_str):
    format_d = dict()
    num = 0
    for s in format_str.split(","):
        ss = s.split(":")
        if len(ss) == 1:
            name = ss[0]
            num += 1
        elif len(ss) == 2 and ss[0].isdigit():
            name = ss[1]
            num = int(ss[0])
        else:
            raise ValueError(u"Invalid format: %s", s)
        if len(name) == 0:
            continue
        assert name not in format_d
        format_d[name] = num-1
    return format_d


def parse_listfile(list_file, format_str):
    format_dict = _get_format_dict(format_str)
    env_dict = dict()
    f = None
    try:
        f = open(list_file, 'rb')
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            td = dict()
            sl = line.split()
            for name, num in format_dict.iteritems():
                if sl[num].isdigit():
                    td[name] = int(sl[num])
                else:
                    td[name] = sl[num]
            host = sl[format_dict["host"]]
            env_dict[host] = td
    finally:
        if f and not f.closed:
            f.close()
    return env_dict

EPILOG = ("\n"
"TIPS:\n"
"1. 固定的环境变量: TPUSH_SRC, TPUSH_HOST, TPUSH_PORT, \n"
"2. 执行过程中可输入命令进行交互控制, 输入 help 查看帮助\n"
"3. 完整的调用命令参考:\n"
"""treepush 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -p $TPUSH_PORT" """
"""/data/datafile $TPUSH_HOST:/data/datafile' -r 3 -m 4 -s 1.1.1.1 -l dest_hosts.txt\n"""
"""treepush 'ssh -o StrictHostKeyChecking=no -p $TPUSH_PORT root@$TPUSH_HOST "ip addr show"' """
"""-r 3 -m 4 -s 1.1.1.1 -l dest_hosts.txt\n\n"""
).decode("utf8")

def main():
    from optparse import OptionParser
    OptionParser.format_epilog = lambda self, epilog: self.epilog   # 重写 format_epilog(), 默认的方法会自动去掉换行
    parser = OptionParser(usage=u"Usage: %prog cmd -l <listfile> -s <source_hosts> [optinos]",
                                version="version %s" % __VERSION__,
                                epilog=EPILOG)
    parser.add_option('-d', '--debug', action='store_true', dest='debug', default=False,
                            help=u'开启 debug')
    parser.add_option('-l', '--list', dest='listfile',
                            help=u'目标服务器列表')
    parser.add_option('-f', '--format', dest='format', default='host,port,user',
                            help=(
                                u'为列表文件各字段命名，使用 "," 分隔, 可使用连续多个逗号跳过字段。'
                                u'字段名会被改成全大写并加上 "TPUSH_" 前缀添加到环境变量中。'
                                u'字段名支持使用 "#:<name>" 直接指定第#个字段对应的名字。'
                                u'(host,port,user 这三个字段固定对应: 主机,端口,用户名)'))
    parser.add_option('-s', '--source', dest='source',
                            help=u'版本源机器列表(1.1.1.1,2.2.2.2)')
    parser.add_option('-m', '--max', dest='max_conn', type='int', default=4,
                            help=u'单IP并发连接数限制(default:%default)')
    parser.add_option('-r', '--retry', dest='retry', type='int', default=0,
                            help=u'单个IP出错后的重试次数(default:%default)')
    parser.add_option('--logdir', dest='logdir', type='str', default='logs',
                            help=u'日志输出目录(default:%default)')
    #parser.add_option('--smart', dest='smart', action='store_true', default=False,
    #        help=u'开启智能重连(如果发现源机与目录机不在同一网段则尝试查找同一网段的源并重连)')

    options, other_args = parser.parse_args(sys.argv[1:])
    print_help = False
    if options.listfile is None:
        print >> sys.stderr, u"* 请指定目标服务器列表(-l/--list)"
        print_help = True
    if options.source is None:
        print >> sys.stderr, u"* 请指定源机器列表(-s/--source)"
        print_help = True
    if len(other_args) == 0:
        print >> sys.stderr, u"* 请给出要执行的命令"
        print_help = True
    if options.max_conn > 10:
        print >> sys.stderr, u"sshd_config MaxSessions 默认配置为 10。单IP的并发连接数不可大于该值"
        print_help = True
    if print_help:
        print "="*60
        parser.print_help()
        sys.exit(127)

    options.source_ips = []
    options.port_map = {}
    for host in options.source.split(','):
        if host.find('@') >= 0:
            user, host = host.split('@', 1)
        if host.find(':') >= 0:
            ip, port = host.split(':', 1)
        else:
            ip, port = host, 22
        options.source_ips.append(ip)
        options.port_map[ip] = port

    command = ' '.join(other_args)

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # if os.path.exists(options.logdir):
    #     os.rename(options.logdir, "%s.%d" % (options.logdir, int(time.time())))
    if not os.path.exists(options.logdir):
        os.mkdir(options.logdir)

    host_info_dict = parse_listfile(options.listfile, options.format)
    options.host_info = host_info_dict

    logger.info("Command: %s", command)
    src_pool = SourcePool(options.max_conn, options.source_ips)
    mgr = TPushManager(src_pool, host_info_dict.keys(), command, options)
    try:
        mgr.main_loop(0.1)
    except KeyboardInterrupt, _:
        logger.fail('#### 操作被中断')
    finally:
        mgr.finish()

if __name__ == '__main__':
    main()
