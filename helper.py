# coding: utf8
__author__ = 'JinXing'

import os
import struct
import socket
import tempfile
import subprocess

from globals import G_OPTIONS


def subprocess_ssh(host, cmd, env=None, logfile=None, _port=22):
    port = int(_port)
    ssh_control_dir = os.path.join(tempfile.gettempdir(), '.tpush_ssh_control')

    if not os.path.exists(ssh_control_dir):
        os.mkdir(ssh_control_dir)
    ssh_control_socket_file = os.path.join(ssh_control_dir, '%s_%d.sock' % (host, port))

    ssh_args = []
    if not os.path.exists(ssh_control_socket_file):
        ssh_args.append('-M')
    ssh_args.extend(['-o', 'ControlPath="%s"' % ssh_control_socket_file])
    ssh_args.extend(['-p', str(port)])
    ssh_args.extend(['-A', '-T'])
    ssh_args.extend(['-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'ConnectTimeout=4'])
    ssh_args.append(host)
    if env:
        for name, value in env.items():
            ssh_args.append("export %s=%s;" % (name, value))
    ssh_args.append("echo '%s:%s ssh connection success';" % (host, port))  # 用于判断连接在哪一层被断开
    ssh_args.append("sleep $((RANDOM%10+5));")  # 如果命令执行过快会出错(连接过快，被拒绝), 这里添加一个随机延时
    ssh_args.append(cmd)

    if logfile is not None:
        r_stdout = open(logfile, 'ab')
    else:
        r_stdout = subprocess.PIPE
    r_stdout.write('ssh '+' '.join(ssh_args)+'\n')
    p = subprocess.Popen(['/usr/bin/ssh']+ssh_args, shell=False, close_fds=True,
                         stdin=subprocess.PIPE, stdout=r_stdout, stderr=subprocess.STDOUT)
    return p


def get_optlist_by_listfile(list_file):
    optlist = []
    fp = open(list_file, 'rb')
    for server in fp:
        if server.find('#') >= 0:
            continue    # 注释行
        t_list = map(lambda x: x.strip("\"'"), server.split())
        server_name = t_list[0]
        server_ip = t_list[1]
        server_sshport = t_list[2]
        optlist.append((server_name, server_ip, server_sshport))
    return optlist


def create_listfile_by_optlist():
    raise


def ip2long(ip_string):
    return struct.unpack('!I', socket.inet_aton(ip_string))[0]


def long2ip(ip_int):
    return socket.inet_ntoa(struct.pack('!I', ip_int))


def get_subnet(ip):
    ip_split = ip.split('.')
    if len(ip_split) != 4:
        raise ValueError(u"Invalid ip address %s" % ip)
    subnet = '.'.join(ip_split[:3])    # 以IP的前3段做为网段
    return subnet


def get_sshport_by_ip(ip):
    if ip in G_OPTIONS.sshport_map:
        return int(G_OPTIONS.sshport_map[ip])
    else:
        return 22