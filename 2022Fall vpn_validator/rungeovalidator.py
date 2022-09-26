# -*- coding: utf-8 -*-
#! /usr/bin/python3
#
# Copyright 2019, 2020, 2021
#                      Zack Weinberg <zackw@panix.com> &
#                      Shinyoung Cho <shicho@cs.stonybrook.edu>
#
# This program is free software:  you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  See the file LICENSE in the
# top level of the source tree containing this file for further details,
# or consult <https://www.gnu.org/licenses/>
"""Orchestrate the whole process for vpn validator.
"""

"""
 Orchestrate the whole process for vpn validator.
"""

import os
import time
import argparse
import vpnconfigs
import vpnvalidator
import logging
import datetime
import schedule


def parse_args()->:
 """Setup for the pragrams to run
 
 Args:
    None
 
 Returns: 
    parser.parse_args()
 """
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', '-d', dest='download', default=True,
                        help='Download config files (TRUE/FALSE)')
    parser.add_argument('--run', '-r', dest='run', default=False,
                        help='Run ping experiments (TRUE/FALSE)')
    parser.add_argument('--config-path', dest='config_path', default='configs/',
                        help='Path for config')
    parser.add_argument('--auth-path', dest='auth_path', default='auth/',
                        help='Path for auth_files')
    parser.add_argument('--ping-parallel', dest='ping_parallel', default='80',
                        help='Parallel')
    parser.add_argument('--centinel-config-path', dest='centinel_config_path', default=None,
                        help='Path for config')
    parser.add_argument('--periodic', dest='periodic', action='store_true',
                        help='Repeat tests periodically (once a week)')

    return parser.parse_args()


def run_once(args: str) -> :
    """Entry point for vpn location validation
    
    Args:
        args:
     
    Returns:
        vpnvalidator.start: to make vpnvalidator run
        logging.info: run the experiments
    
    """

    # open a new log file each time we run
    if not os.path.exists('logs/'):
        os.makedirs('logs/')
    curr = datetime.datetime.now()
    log_filename = 'logs/%04d-%02d-%02d-%02dh_runtime.log' % (curr.year, curr.month, curr.day, curr.hour)
    logging.basicConfig(filename=log_filename, filemode='w+', level=logging.DEBUG,
                        format='[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s]: %(message)s',
                        datefmt='%Y%m%d %H:%M:%S')

    # download config files
    fname_config = 'vpn_configs.csv'
    fname_failed = 'vpn_configs_failed_downloading.csv'
    if args.download:
        s_time = time.time()
        vpnconfigs.download(args.config_path, fname_config, fname_failed)
        logging.info("Execution time to download all configs: %s seconds."
                     % (time.time() - s_time))
    # run experiments
    if args.run:
        s_time = time.time()
    #     #downloaded
        if not args.download and \
            not os.path.exists(os.path.join(args.config_path, fname_config)) or \
            not os.path.exists(os.path.join(args.config_path, 'hma/ca.crt')) or \
            not os.path.exists(os.path.join(args.config_path, 'hma/hmauser_auth.key')) or \
            not os.path.exists(os.path.join(args.config_path, 'hma/hmauser.key')) or \
            not os.path.exists(os.path.join(args.config_path, 'ipvanish/ca.ipvanish.com.crt')) or \
            not os.path.exists(os.path.join(args.config_path, 'purevpn/ca.crt')) or \
            not os.path.exists(os.path.join(args.config_path, 'purevpn/Wdc.key')):
            logging.error("Providers' key or crt are missing. Download them first.")
            return
        if not os.path.exists(os.path.join(args.auth_path, 'auth_file_hma')) or \
            not os.path.exists(os.path.join(args.auth_path, 'auth_file_ipvanish')) or \
            not os.path.exists(os.path.join(args.auth_path, 'auth_file_purevpn')):
            logging.error("Auth files are missed. Add auth files in the folder:"
                          " %s/{each provider}." % args.config_path)
            return
        vpnvalidator.start(args.config_path, fname_config, args.centinel_config_path,
                           args.auth_path, args.ping_parallel)
        logging.info("Execution time to run all experiments: %s seconds."
                     % (time.time() - s_time))

def run_schedule(args: str) -> None:
    """The time to run the programs

    Args:
        args:

    Returns:
        None
        
    """
    schedule.every().week.at("03:00").do(lambda: run_once(args))

def main() -> None:
 """Command line main function.
 
 Args: 
    None
 
 Returns:
    None
    
 """
    args = parse_args()
    if args.periodic:
        run_schedule(args)
    else:
        run_once(args)
    #vpnvalidator.GoogleDNSQuery()

if __name__ == "__main__":
    main()
