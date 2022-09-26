# -*- coding: utf-8 -*-
import csv
import os
import logging
import json
import shutil
import datetime
import time
import openvpn
import config
#import dns.resolver
#import ipinfo
from urllib.request import urlopen
# import retrieve_landmarks as rl

#from urllib2 import urlopen, URLError

"""
vpn sanitizer: program to determine whether if a vpn node is in the claimed location. 
The process works in the following workflow:

1. Obtain .csv file containing basic info on the node and parse relevant information.
    Requisites: 
        i. Must contain path to .csv file
        2. Must have a working internet connection.
    Subflow:
    a. open .csv file
    b. parse data into a list.
    c. save data.
2. Connect using openvpn, to the particular VPN node.
    a. obtain both .crt and config file paths.
    b. Generate credential text file. 
    c. obtain tls_auth and key direction params. (might be predefined.)
    d. connect to the particular VPN.
    python getting date format nicely
3. if successful, use the terminal and execute: 
    ./vpn-sanity-check --parallel 10 --port 80 
    <local IP> <testing country, iso3> landmarks-and-distances.csv.gz > output.json
4. Obtain json file, and process it: (save it) 
"""

LANDMARKS_AND_DISTANCES = 'landmarks-and-distances.csv.gz'
NUMBER_OF_PARALLEL_PROCESSES = '80'
PORT_NUMBER = '80'
MIN_REACHABLE = '50'

DIR_VPN_CHECKER = '../../rust/target/release/'
VPN_CHECKER = 'vpn-sanity-check'

curr = datetime.datetime.now()
START_DATE = '%04d-%02d-%02d' % (curr.year, curr.month, curr.day)
DIR_GOOD_CONFIGS = 'positive-configs/' + START_DATE
DIR_WALKERS = '/qemu/walkers/{vpn}_walker/walk_{vpn}/'

ERROR_NODES = 0
FAILED_NODES = 0
PASSED_NODES = 0


def _run_experiment(config_path: str, claimed_country: str, campus_server_ip: str)-> str:
    """ Run "vpn-sanity-check"

    Args:
        config_path: path of config file
        claimed_country: the country claimed for VPN
        campus_server_ip: the ip address of campus sever

    Return:
        the josh path

    """
    global NUMBER_OF_PARALLEL_PROCESSES
    global LANDMARKS_AND_DISTANCES
    global DIR_VPN_CHECKER
    global VPN_CHECKER
    global PORT_NUMBER
    global START_DATE
    global MIN_REACHABLE

    # create directory if it does not exist
    date_dir = 'json-outputs/%s/' % START_DATE
    os.makedirs(date_dir, exist_ok=True)

    # create json
    output_path = date_dir + '%s.json' % (config_path.split("/")[-1])
    output_json = open(output_path, "w+")

    # retrieve landmarks if LANDMARKS_AND_DISTANCES does not exist or is outdated ( >15 days).
    if not os.path.exists(LANDMARKS_AND_DISTANCES) or \
        (time.time() - os.path.getctime(LANDMARKS_AND_DISTANCES)) > (15 * 24 * 60 * 60):
        # rl.write_active_anchor_list(rl.retrieve_active_anchor_list())

        logging.info("Start retrieving data on all of the publicly accessible RIPE anchors.")
        os.system("python3 retrieve_landmarks.py > landmarks.csv")
        logging.info("Completed retrieving RIPE anchors.")

        logging.info("Start analyzing the locations of the RIPE landmarks.")
        dir_data = "../../data"
        os.system("python3 analyze_landmarks.py {0} landmarks.csv {1}/ne_10m_admin_0_map_units.zip "
                  "{1}/merges.yml {1}/iso3166.csv".format(LANDMARKS_AND_DISTANCES, dir_data))

    cmd = ' ./%s --parallel %s -m %s --port %s %s %s %s > %s' \
          % (DIR_VPN_CHECKER + VPN_CHECKER, NUMBER_OF_PARALLEL_PROCESSES, MIN_REACHABLE,
          PORT_NUMBER, campus_server_ip, claimed_country, LANDMARKS_AND_DISTANCES, output_path)

    logging.info('Performing shell command: \'%s\'' % cmd)
    os.system(cmd)

    output_json.close()

    return output_path


def return_abs_path(directory: str, path: str)->str:
    """ Unfortunately, Python is not smart enough to return an absolute
    path with tilde expansion, so I writing functionality to do this

    Args:
        directory: the directory after experiencing os.path.expanduser
        path: the path need to be processed

    Return:
        the normalized version of the pathname path

    """
    if directory is None or path is None:
        return
    directory = os.path.expanduser(directory)
    return os.path.abspath(os.path.join(directory, path))


def _create_config_files(base_path: str, vpn_provider: str, vpn_ip: str, hostname: str, claimed_iso3: str, filename: stry):
    """
    For each VPN file in directory/vpns, create a new configuration
    file and all the associated directories
    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    -----results (contains the results)
    :param directory:
    """
    global DIR_WALKERS

    logging.info("Starting to create config files from openvpn files")

    conf_dir = return_abs_path(base_path, "configs")
    os.makedirs(conf_dir, exist_ok=True)
    home_dirs = return_abs_path(base_path, "home")
    os.makedirs(home_dirs, exist_ok=True)


    configuration = config.Configuration()
    # setup the directories
    os.makedirs(home_dirs, exist_ok=True)

    exp_dir = os.path.join(home_dirs, filename, "experiments")
    os.makedirs(exp_dir, exist_ok=True)

    data_dir = os.path.join(home_dirs, filename, "data")
    os.makedirs(data_dir, exist_ok=True)

    res_dir = os.path.join(home_dirs, filename, "results")
    os.makedirs(res_dir, exist_ok=True)

    # the path should be the path that walkers know
    home_dir = os.path.join(DIR_WALKERS.replace('{vpn}', vpn_provider) + 'home', filename)
    configuration.params['user']['centinel_home'] = home_dir

    exp_dir = os.path.join(home_dir, "experiments")
    configuration.params['dirs']['experiments_dir'] = exp_dir

    data_dir = os.path.join(home_dir, "data")
    configuration.params['dirs']['data_dir'] = data_dir

    res_dir = os.path.join(home_dir, "results")
    configuration.params['dirs']['results_dir'] = res_dir

    log_file = os.path.join(home_dir, "centinel.log")
    configuration.params['log']['log_file'] = log_file
    login_file = os.path.join(home_dir, "login")
    configuration.params['server']['login_file'] = login_file

    configuration.params['user']['is_vpn'] = True
    # we have to keep these information to debugging later
    configuration.params['user']['hostname'] = hostname
    configuration.params['user']['connected_ip'] = vpn_ip
    configuration.params['user']['claimed_country'] = claimed_iso3

    configuration.params['server']['verify'] = True
    configuration.params['experiments']['tcpdump_params'] = ["-i", "tun0"]

    conf_file = os.path.join(conf_dir, filename)
    configuration.write_out_config(conf_file)


def _make_directory(vpn_provider: str, path_to_ovpn_file: str, vpn_ip: str, hostname: str, claimed_iso3: str)->None:
    """ function to make a directory of sanitized vpn nodes.

    Args:
        vpn_provider: name of vpn provider
        path_to_ovpn_file: the path to target ovpn file
        vpn_ip: the ip of vpn
        hostname: the name of the host
        claimed_iso3: the country name

    Return:
        None
    """
    # create a base path in where the files will be saved.
    global DIR_GOOD_CONFIGS
    base_path = os.path.join(DIR_GOOD_CONFIGS, vpn_provider)

    vpn_path = return_abs_path(base_path, 'vpns')
    os.makedirs(vpn_path, exist_ok=True)

    # copy provider's ovpn file to vpn_path
    fname = path_to_ovpn_file.split('/')[-1]
    file_vpn_path = os.path.join(vpn_path, fname)
    try:
        shutil.copy(path_to_ovpn_file, file_vpn_path)
    except OSError:
        logging.error('OS ERROR is occurred: %s' % path_to_ovpn_file)
    except IOError:
        # print 'IO Error'
        logging.error('IO ERROR is occurred: %s' % path_to_ovpn_file)

    _create_config_files(base_path, vpn_provider, vpn_ip, hostname, claimed_iso3, fname)


def _get_results(output_json: str, config_path: str, provider: str, vpn_ip: str, hostname: str, claimed_iso3: str)->None:
    """ Searches for a particular file in a set directory.

        Args:
            output_json: the name of the file to open
            config_path: the path of config file
            vpn_ip: the ip of vpn
            hostname: the name of host
            claimed_iso3: the claimed country

        Return:
            None

     """
    global FAILED_NODES
    global PASSED_NODES

    try:
        with open(output_json) as json_file:
            logging.debug('Attempting to read json file...')
            data = json.load(json_file)
            if data['verified'] == True:
                logging.info('Clean VPN node at: %s' % config_path)
                PASSED_NODES = PASSED_NODES + 1
                #may comment out if there are errors occur
                _make_directory(provider, config_path, vpn_ip, hostname, claimed_iso3)
                return True
            else:
                logging.info('False vpn Node at: %s' % config_path)
                FAILED_NODES = FAILED_NODES + 1
                return False
    except IOError:
        logging.error("%s: IO ERROR has occurred. No json output file found..." % config_path)

    return None


def get_external_ip()->None:
    """ Searches for a particular file in a set directory.

        Args:
            None

        Return:
            None
    """
    # pool of URLs that returns public IP
    url_list = ["https://whatismyip.org",
                "https://api.ipify.org/"]
    # "https://wtfismyip.com/text",
    # "http://ip.42.pl/raw",
    # "http://myexternalip.com/raw",
    # try four urls in case some are unreachable
    for url in url_list:
        try:
            my_ip = urlopen(url, timeout=5).read().rstrip()
            return my_ip
        except Exception as e:
            logging.warning("Failed to connect to %s: %s" % (url, e))
            continue
    # return None if all failed
    return None


def search_for_filetype(directory: str, filetype: str )-> str:
    """ Searches for a particular file in a set directory.

   Args:
        directory: the directory of
        filetype: the suffix of datatype

   Return:
        the concatenated path components

    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(filetype):
                return os.path.join(root, file)

#ip address: 144.121.36.212
#previous campus server: 128.119.240.136
def _start_openvpn(directory: str, vpn_info: str, local_ip_address: str, auth_path: str, campus_server_ip='128.119.240.136') -> None:
    """Connect to VPN to run experiments

    Args:
        directory: the directory of config file
        vpn_info: the information of vpn
        local_ip_address : local IP
        auth_path: path of authentication
        campus_server_ip: the IP of campus server

    Return:
        call the result of calling method _get_results

    """
    global ERROR_NODES
    global FAILED_NODES
    global PASSED_NODES

    vpn_ip = vpn_info[0]
    provider = vpn_info[1]
    hostname = vpn_info[2]
    claimed_iso3 = vpn_info[4]
    config_path = vpn_info[5]

    provider_dir = os.path.join(directory, provider)
    auth_file = os.path.join(auth_path, 'auth_file_' + provider)
    crt_file = search_for_filetype(provider_dir, '.crt')
    tls_auth = None
    key_direction = None
    # if provider == 'purevpn':
    #     key_direction = '1'
    #     tls_auth = os.path.join(provider_dir, 'Wdc.key')
    if provider == 'hma':
        tls_auth = os.path.join(provider_dir, 'hmauser.key')

    logging.info("Starting VPN: %s" % config_path)
    logging.debug("auth_file: %s" % auth_file)
    logging.debug("config_file: %s" % config_path)
    logging.debug("crt_file: %s" %crt_file)
    logging.debug("tls_auth: %s" %tls_auth)
    logging.debug("key_direction: %s" %key_direction)

    connection = openvpn.OpenVPN(timeout=60, auth_file=auth_file, config_file=config_path,
                                 crt_file=crt_file, tls_auth=tls_auth, key_direction=key_direction)
    # start VPN
    connection.start()

    if not connection.started:
        logging.error("%s: Failed to start VPN_node." % config_path)
        connection.stop()
        time.sleep(5)
        ERROR_NODES = ERROR_NODES + 1
        return None

    logging.info('Connected to vpn node successfully.'
                 ' VPN provider: %s hostname: %s, iso3_country: %s, path: %s'
                 % (provider, hostname, claimed_iso3, config_path))

    # TODO: need to figure out: when using purvpn's VPN, openvpn creats a tun0
    #    interface with the given IP, but somehow the external ip is the same with local IP.
    #    so far, we used 128.119.240.136, but now it returns time-out.
    current_ip = get_external_ip()
    logging.info("%s: Connected external IP is: %s" % (config_path, current_ip))

    # if the external IP hasn't changed after connecting to VPN server
    if local_ip_address == current_ip:
        logging.error("%s: External IP address of this VPN has not changed." % config_path)
        connection.stop() # TODO: need resolve the cases when the program cannot stop OpenVPN
        time.sleep(5)
        ERROR_NODES = ERROR_NODES + 1
        return None

    # run pings + validator
    output_json = None
    try:
        # TODO: need to check if campus_server_ip is alive.
        #       This is to subtract the ping time from local machine to VPN end point
        output_json = _run_experiment(config_path, claimed_iso3, campus_server_ip)
    except Exception as exp:
        logging.exception("%s: Error running vpn-sanity-check: %s" % (config_path, exp))

    # stop VPN
    logging.info("%s: Stopping VPN." % config_path)
    connection.stop()
    time.sleep(5)

    current_ip = get_external_ip()
    if local_ip_address != current_ip:
        logging.error("VPN still connected! IP: %s" % current_ip)
        if len(openvpn.OpenVPN.connected_instances) != 0:
            logging.warning("Trying to disconnect VPN")
            for instance in openvpn.OpenVPN.connected_instances:
                instance.stop()
                time.sleep(5)
        current_ip = get_external_ip()
        if current_ip is None or current_ip != local_ip_address:
            logging.error("Stopping VPN failed! Exiting...")
            return None
        logging.info("Disconnecting VPN successfully")

    # get result from .json file.
    if output_json is None or (os.path.getsize(output_json) == 0):
        return None

    logging.info('Checking file size of output_json output file from shell command. '
                 'Size for path: %s is : %s bytes.'
                 % (output_json, os.path.getsize(output_json)))
    result = _get_results(output_json, config_path, provider, vpn_ip, hostname, claimed_iso3)

    return result


def start(config_dir: str, config_fname: str, auth_path: str, centinel_positive_path: str, centinel_config_path: str, ping_parallel: str)->None:
    """ Starts the VPN sanitizer process

        Args:
           config_dir: path of config file. have a fixed value assigned in main below
           config_fname: the path component to be joined
           auth_path: path of authentication
           centinel_positive_path: path of centinel of positive?
           centinel_config_path: path of centinel config? (maybe for requisites)
           ping_parallel: the number of parallel process

       Returns:
           None

    """
    line_count = 0
    global START_DATE
    global ERROR_NODES
    global FAILED_NODES
    global PASSED_NODES
    global DIR_GOOD_CONFIGS
    global NUMBER_OF_PARALLEL_PROCESSES
    NUMBER_OF_PARALLEL_PROCESSES = ping_parallel

    # get current ip address.
    local_ip_address = get_external_ip()
    logging.info("Local IP address is %s." % local_ip_address)

    with open(os.path.join(config_dir, config_fname), "r") as fi:
        with open(os.path.join(config_dir,
                               config_fname.split('.csv')[0] + '_results.csv'), "w") as fo:
            csv_reader = csv.reader(fi, delimiter=',')
            csv_writer = csv.writer(fo, delimiter=',')
            for vpn_info in csv_reader:
                line_count += 1
                if line_count == 1:
                    logging.info('Starting tests...')
                    csv_writer.writerow(vpn_info + ['verified'])
                    continue

                # Start openvpn
                #make sure that start_openvpn is working correctly
                result = _start_openvpn(config_dir, vpn_info, local_ip_address, auth_path)
                csv_writer.writerow(vpn_info + [result])


    logging.info('Scanned a total of %s nodes.' % (line_count - 1))
    logging.info('Total validated nodes: %s' % PASSED_NODES)
    logging.info('Total failed nodes: %s' % FAILED_NODES)
    logging.info('Total error nodes: %s' % ERROR_NODES)


    # symlink to new folder
    if (centinel_config_path is not None) and (centinel_positive_path is not None):
        logging.info("Copying configs.")
        cmd = f"cp -r {DIR_GOOD_CONFIGS} {centinel_positive_path}"
        os.system(cmd)
        logging.info("Creating symlink.")
        for provider in ['hma', 'ipvanish', 'purevpn']:
            src = os.path.join(centinel_positive_path, START_DATE, provider, 'home')
            dst = os.path.join(centinel_config_path, provider + '_walker/walk_' + provider + '/home')
            os.symlink(src, dst)
            src = os.path.join(centinel_positive_path, START_DATE, provider, 'vpn')
            dst = os.path.join(centinel_config_path, provider + '_walker/walk_' + provider + '/vpn')
            os.symlink(src, dst)
            src = os.path.join(centinel_positive_path, START_DATE, provider, 'configs')
            dst = os.path.join(centinel_config_path, provider + '_walker/walk_' + provider + '/configs')
            os.symlink(src, dst)
            # os.symlink(src, dst)

    return


# def GoogleDNSQuery():
#     googleDNS = dns.resolver.Resolver()
#     googlePublicIP = '8.8.8.8'
#     googleDNS.nameservers = [googlePublicIP]
#     googleResult = googleDNS.query('google.com')
#     for ipval in googleResult:
#         print("google ip", ipval)
#         print("google location", ip_to_location(ipval.address))
#     cloudDNS = dns.resolver.Resolver()
#     cloudPublicIP = '1.1.1.1'
#     cloudDNS.nameservers = [cloudPublicIP]
#     cloudResult = cloudDNS.query('cloudflare.com')
#     for ipval2 in cloudResult:
#         print("CloudFlare IP", ipval2)
#         print("CloudFlare location", ip_to_location(ipval2.address))
#
#
# def ip_to_location(ipaddress):
#     access_token = "3a9476f4022438"
#     handler = ipinfo.getHandler(access_token)
#     details = handler.getDetails(ipaddress)
#     return details.country_name, details.city



if __name__ == "__main__":
    import datetime
    # open a new log file each time we run
    if not os.path.exists('logs/'):
        os.makedirs('logs/')
    curr = datetime.datetime.now()
    log_filename = 'logs/%04d-%02d-%02d_runtime.log' % (curr.year, curr.month, curr.day)
    logging.basicConfig(filename=log_filename, filemode='w+', level=logging.DEBUG,
                        format='[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s]: %(message)s',
                        datefmt='%Y%m%d %H:%M:%S')

    config_fname = 'vpn_configs.csv'
    centinel_config_path = 'configs/'
    #centinel_config_path = '/home/iclab-walkers/walkers'
    auth_path = 'auth/'
    # auth_path = '/opt/vpn-validation/verifier_auths'
    num_parallel = '10'
    # num_parallel = '80'
    centinel_positive_path = None
    # centinel_positive_path = '/opt/vpn-validation/walker_shared'
    centinel_config_path = None
    # centinel_config_path = '/opt/vpn-validation/'
    start('configs/', config_fname, auth_path, centinel_positive_path, centinel_config_path, num_parallel)
    #GoogleDNSQuery()
