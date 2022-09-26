#!/usr/bin/python
# openvpn.py: library to handle starting and stopping openvpn instances

import logging
import os
import signal
import subprocess
import threading
import time


class OpenVPN:
    connected_instances = []
    """
    For each VPN, check if there are experiments and scan with it if
    necessary
    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    :param config_file: the config file for a particular vpn node.
    :param auth_file: a text file with username at first line and
                      password at second line
    :param crt_file: optional root certificate file
    :param tls_auth: additional key
    :param key_direction: must specify if tls_auth is used
    :param timeout: grace time to determine whether if a connection has timed out or not.
    :return:
    """
    def __init__(self, config_file=None, auth_file=None, crt_file=None,
                 tls_auth=None, key_direction=None, timeout=60) ->None:
        """Setup for OpenVPN

        Args:
            Config_file: the config file for a particular vpn node.
            auth_file: a text file with username at first line and
                      password at second line
            crt_file: optional root certificate file
            tls_auth: additional key
            key_direction: must specify if tls_auth is used
            timeout: grace time to determine whether if a connection has timed out or not.

        Returns:
            None

        """
        self.started = False
        self.stopped = False
        self.error = False
        self.notifications = ""
        self.auth_file = auth_file
        self.crt_file = crt_file
        self.tls_auth = tls_auth
        self.key_dir = key_direction
        self.config_file = config_file
        self.thread = threading.Thread(target=self._invoke_openvpn)
        self.thread.setDaemon(1)
        self.timeout = timeout

    def _invoke_openvpn(self) -> None:
        """Invoke openvpn

        Args:
            None

        Returns:
            None

        """
        cmd = ['sudo', 'openvpn', '--script-security', '2']
        # --config must be the first parameter, since otherwise
        # other specified options might not be able to overwrite
        # the wrong, relative-path options in config file
        if self.config_file is not None:
            cmd.extend(['--config', self.config_file])
        if self.crt_file is not None:
            cmd.extend(['--ca', self.crt_file])
        if self.tls_auth is not None and self.key_dir is not None:
            cmd.extend(['--tls-auth', self.tls_auth, self.key_dir])
        if self.auth_file is not None:
            cmd.extend(['--auth-user-pass', self.auth_file])
        # self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        # print(' '.join(cmd))
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
        self.kill_switch = self.process.terminate
        self.starting = True
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                break
            self.output_callback(line, self.process.terminate)


    def output_callback(self, line, kill_switch) -> None:
        """Set status of openvpn according to what we process

        Args:
            line: the line in a file waiting to be used for openvpn
            kill_switch:a feature that prevents your device from making unprotected connections.

        Returns:
            None

        """
        #self.notifications += line + "\n"
        self.notifications = line.decode('UTF-8') + "\n"
        if "Initialization Sequence Completed" in self.notifications:
            self.started = True
        if "ERROR:" in self.notifications or "Cannot resolve host address:" in self.notifications:
            self.error = True
        if "process exiting" in self.notifications:
            self.stopped = True

    def start(self, timeout=None) -> None:
        """Start OpenVPN and block until the connection is opened or there is
        an error

        Args:
            timeout: time in seconds to wait for process to start

        Returns:
            None

        """
        if not timeout:
            timeout = self.timeout
        self.thread.start()
        start_time = time.time()
        while start_time + timeout > time.time():
            self.thread.join(1)
            if self.error or self.started:
                break
        if self.started:
            logging.info("OpenVPN connected")
            # append instance to connected list
            OpenVPN.connected_instances.append(self)
        else:
            logging.warning("OpenVPN not started")
            for line in self.notifications.split('\n'):
                logging.warning("OpenVPN output:\t\t%s" % line)

    def stop(self, timeout=None) -> None:
        """Stop OpenVPN process group

        Args:
            timeout: time in seconds to wait for process to stop

        Returns:
            None

        """
        if not timeout:
            timeout = self.timeout
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        #self.process.send_signal(signal.CTRL_BREAK_EVENT)
        self.process.kill()
        #os.kill(self.process.pid, signal.SIGTERM)
        self.thread.join(timeout)
        if self.stopped:
            logging.info("OpenVPN stopped")
            if self in OpenVPN.connected_instances:
                OpenVPN.connected_instances.remove(self)
        else:
            logging.error("Cannot stop OpenVPN!")
            for line in self.notifications.split('\n'):
                logging.warning("OpenVPN output:\t\t%s" % line)
