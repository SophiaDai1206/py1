#! /usr/bin/python3
#
#
"""Downloading and parsing all relevant information of vpn provider's vpn nodes
"""

import csv
import contextlib
import logging
import os
import pycountry
import requests
import shutil
import socket
import sys
import urllib
import zipfile

# to resolve: urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1108)>
# https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
# import ssl
# import certifi
# ssl._create_default_https_context = ssl._create_unverified_context
# import urllib3


HMA_COUNTRY_RENAMES = {'AlandIslands': ('ALA', 'Aland Islands'),
                       'USA': ('USA', 'United States'),
                       'AmericanSamoa': ('ASM', 'American Samoa'),
                       'Bolivia': ('BOL', 'Bolivia'),
                       'AntiguaandBarbuda': ('ATG', 'Antigua and Barbuda'),
                       'Bosnia': ('BIH', 'Bosnia and Herzegovina'),
                       'BritishVirginIslands': ('VGB', 'Virgin Islands, British'),
                       'Brunei': ('BRN', 'Brunei Darussalam'),
                       'CapeVerde': ('CPV', 'Cabo Verde'),
                       'CocosIslands': ('CCK', 'Cocos (Keeling) Islands'),
                       'Coted`Ivoire': ('CIV', 'Cote d\'Ivoire'),
                       'CzechRepublic': ('CZE', 'Czechia'),
                       'FalklandIslands': ('FLK', 'Falkland Islands (Malvinas)'),
                       'Guinea-Bissau': ('GIN', 'Guinea'),
                       'Iran': ('IRN', 'Iran, Islamic Republic of'),
                       'Laos': ('LAO', 'Lao People\'s Democratic Republic'),
                       'Macau': ('MAC', 'Macao Special Administrative Region of China'),
                       'Macedonia': ('MKD', 'North Macedonia'),
                       'Moldova': ('MDA', 'Moldova, Republic of'),
                       'NorthKorea': ('PRK', 'Korea, Democratic People\'s Republic of'),
                       'Palestine': ('PSE', 'Palestine, State of'),
                       'PitcairnIslands': ('PCN', 'Pitcairn'),
                       'RepublicofDjibouti': ('DJI', 'Djibouti'),
                       'RepublicofSingapore': ('SGP', 'Singapore'),
                       'RepublicoftheCongo': ('COD', 'Congo'),
                       'Russia': ('RUS', 'Russian Federation'),
                       'SaintHelena': ('SHN', 'Saint Helena, Ascension and Tristan da Cunha'),
                       'SaintKittsandNevis': ('KNA', 'Saint Kitts and Nevis'),
                       'SaintPierreandMiquelon': ('SPM', 'Saint Pierre and Miquelon'),
                       'SaintVincentandtheGrenadines': ('VCT', 'Saint Vincent and the Grenadines'),
                       'SaoTomeandPrincipe': ('STP', 'Sao Tome and Principe'),
                       'SouthKorea': ('KOR', 'Korea, Republic of'),
                       'SvalbardandJanMayen': ('SJM', 'Svalbard and Jan Mayen'),
                       'Swaziland': ('SWZ', 'Eswatini'),
                       'Sweden': ('SWE', 'Sweden'),
                       'Syria': ('SYR', 'Syrian Arab Republic'),
                       'Taiwan': ('TWN', 'Taiwan, Province of China'),
                       'Tanzania': ('TZA', 'Tanzania, United Republic of'),
                       'TrinidadandTobago': ('TTO', 'Trinidad and Tobago'),
                       'TurksandCaicosIslands': ('TCA', 'Turks and Caicos Islands'),
                       'UK': ('GBR', 'United Kingdom'),
                       'Vatican': ('VAT', 'Holy See (Vatican City State'),
                       'Venezuela': ('VEN', 'Venezuela, Bolivarian Republic of'),
                       'Vietnam': ('VNM', 'Viet Nam'),
                       'PapuaNewGuinea': ('PNG', 'Papua New Guinea Alotau'),
                       'ChristmasIsland': ('CXR', 'Christmas Island'),
                       'SaintLucia': ('LCA', 'Saint Lucia'),
                       'UnitedArabEmirates': ('ARE', 'United Arab Emirates'),
                       'CentralAfricanRepublic': ('CAF', 'Central African Republic'),
                       'BurkinaFaso': ('BFA', 'Burkina Faso'),
                       'HongKong': ('HKG', 'Hong Kong'),
                       'DominicanRepublic': ('DOM', 'Dominican Republic'),
                       'SolomonIslands': ('SLB', 'Solomon Islands'),
                       'SaudiArabia': ('SAU', 'Saudi Arabia'),
                       'NewCaledonia': ('NCL', 'New Caledonia'),
                       'ElSalvador': ('SLV', 'El Salvador'),
                       'CaymanIslands': ('CYM', 'Cayman Islands'),
                       'CookIslands': ('COK', 'Cook Islands'),
                       'PuertoRico': ('PRI', 'Puerto Rico'),
                       'SouthAfrica': ('ZAF', 'South Africa'),
                       'SanMarino': ('SMR', 'San Marino'),
                       'SriLanka': ('LKA', 'Sri Lanka'),
                       'NewZealand': ('NZL', 'New Zealand'),
                       'FaroeIslands': ('FRO', 'Faroe Islands'),
                       'EquatorialGuinea': ('GNQ', 'Equatorial Guinea'),
                       'CostaRica': ('CRI', 'Costa Rica'),
                       'NorfolkIsland': ('NFK', 'Norfolk Island')
                       }


def urlretrieve(url: str, filename: str) -> None:
    """Retrieve url from the file

    Args:
        url: url that we want
        filename: the name of file

    Returns:
        None

    """
    # isseu: urllib.error.HTTPError: HTTP Error 403: Forbidden
    # to resolve:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with open(filename, 'wb') as out_file, \
        contextlib.closing(urllib.request.urlopen(req)) as in_stream:
         # contextlib.closing(urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()))) as in_stream:
        while True:
            block = in_stream.read(8192)
            if not block:
                break
            out_file.write(block)


class DownloadVPNConfigs():

    def __init__(self, directory: str, fname_config: str, fname_failed: str) -> None:
        """Setup for the class of downloadVPNconfigs

        Args:
            directory: the collection where you want this to happen
            fname_config: The name of config file
            fname_failed: Config file that we could not find VPN node information from it

        Returns:
            None

        """
        self.directory = directory
        self.path_to_config = os.path.join(directory, fname_config)
        self.path_to_failed = os.path.join(directory, fname_failed)
        self.number_of_scans = 5

    def _copy_ovpn_file_and_modify_hostname(self, path_to_original_ovpn_file: str, provider: str, hostname: str, ip_address: str)-> str:
        """Copies a .ovpn file save for the line specifying the hostname: It will be replaced with the ip address given in the parameters.

        Args:
            path_to_original_ovpn_file: The path to the original vpn file
            provider: name of the vpn provider
            hostname: hostname's url
            ip_address: ip address of the vpn

        Returns:
            duplicate_opvn_dir: duplicated vpn directory

        """
        # ir = path_to_original_ovpn_file.split('/')[0:len(path_to_original_ovpn_file.split('/')) - 2]
        # the change is due to purevpn.
        ir = path_to_original_ovpn_file.split('/')[0:3]

        duplicate_ovpn_dir = ''
        for i in range(len(ir)):
            duplicate_ovpn_dir = duplicate_ovpn_dir + str(ir[i]) + '/'

        duplicate_ovpn_dir = duplicate_ovpn_dir + hostname + '_' + ip_address + '.ovpn'

        with open(path_to_original_ovpn_file, "r") as original_file:
            with open(duplicate_ovpn_dir, "w") as duplicate_file:
                for line in original_file:
                    # if the file line contains the hostname, replace:
                    if (line.startswith('remote')) and not (line.startswith('remote-')):
                        if provider != 'purevpn' and provider != 'ipvanish':
                            duplicate_file.write('remote %s ' % ip_address)
                        else:
                            duplicate_file.write('remote %s %s' % (ip_address, line.split(' ')[2]))
                    else:
                        # otherwise, just copy contents
                        duplicate_file.write(line)
                # add dns update options to each file?? why?
                # https://wiki.archlinux.org/index.php/OpenVPN#Update_systemd-resolved_script ??
                # if provider == 'purevpn' or provider == 'hma':
                duplicate_file.write("\n")
                duplicate_file.write("up /etc/openvpn/update-resolv-conf\n")
                duplicate_file.write("down /etc/openvpn/update-resolv-conf\n")
        return duplicate_ovpn_dir

    def _get_ip_address(self, hostname: str) ->list:
        """ Performs repeated DNS requests as specified and extracts the IP address(es)
        from the DNS response. Returns a list(s) containing the IP address(es). If an additional URL
        has been founds, add automatically, and perform an additional n number of dns requests.

        Args:
            param hostname: hostname's url.

        Returns:
            a list(s) containing the IP address(es).
            
        """
        # logging.info('performing check of ip address %s times' % number_of_checks)
        # Make repeated IP address queries to a host. if a new address is found,
        # repeat the preset amount of queries. If not, stop.
        # number_of_checks: the number of times the DNS request should be repeated if a new ip address has been found
        no_of_grace = 3
        no_of_cosec_succ = 0
        lives = self.number_of_scans
        ips = []
        while lives != 0:
            try:
                query_result = socket.gethostbyname_ex(hostname)
                # print 'Query result: %s' %str(query_result)
                ips += query_result[2]
                no_of_cosec_succ = no_of_cosec_succ + 1
                if no_of_cosec_succ == lives:
                    # print 'successful query of hostname %s with ip of %s' %(hostname, IP)
                    lives = 0
                    return list(set(ips))
            except socket.gaierror:
                logging.exception("FATAL ERROR. Failed to resolve %s" % hostname)
                if no_of_grace == 0:
                    logging.error('FATAL ERROR: Failed to perform DNS request. Aborting particular VPN node.')
                    logging.error('unsuccesful query of hostname %s' % hostname)
                    return 'FAILED'
                lives = lives + 5
                no_of_grace = no_of_grace - 1
        return

    def _country_converter(self, request_type: str, string: str) -> str:
        """ converts either a ISO2 to Country name or vice versa. Uses the pycountry package

        Args:
            request_type: specification of what type of conversion is required.
            Only accepts ISO2_TO_STRING, STRING_TO_ISO2, ISO3_TO_STRING, STRING_TO_ISO3, ISO2_TO_ISO3.
            The operation is defined by the request_type param.
            string: the name of countries

        Returns:
            c.name: Country Name
            c.alpha_3:  ISO3
            c.alpha_2:  ISO2
            string: Exceptions of conversion between ISO2, ISO3 and country names

        """
        logging.info("Converting %s conversion of input: %s" % (request_type, string))
        if request_type == 'ISO2_TO_STRING':
            # change ISO2 to Country Name
            c = pycountry.countries.get(alpha_2=string)
            return c.name
        elif request_type == 'STRING_TO_ISO2':
            # change COuntry Name to ISO2
            c = pycountry.countries.get(name=string)
            return c.alpha_2
        elif request_type == 'ISO3_TO_STRING':
            # change COuntry Name to ISO2
            c = pycountry.countries.get(alpha_3=string)
            return c.name
        elif request_type == 'STRING_TO_ISO3':
            # change COuntry Name to ISO2
            c = pycountry.countries.get(name=string)
            return c.alpha_3
        elif request_type == 'ISO2_TO_ISO3':
            # change COuntry Name to ISO2
            c = pycountry.countries.get(alpha_2=string)
            return c.alpha_3
        else:
            return string

    def _put_space(self, input: str) -> str:
        """function to put space in a string between capital letters.

        Args:
            input: the input information

        Returns:
            output_string: the input information with space

        """
        output_string = ''
        firstLetter = True
        for char in input:
            if char.isupper():
                if firstLetter == True:
                    output_string += char
                    firstLetter = False
                else:
                    output_string += " "
                    output_string += char
            else:
                output_string += char
        return str(output_string)

    def _hma_iso3_convertor(self, filename: str) -> str:
        """ Dealing with typos too; to convert countries information on the file to their ISO3 with names under the hma vpn company

        Args:
            filename: the filename of a file containing countries name

        Returns:
            cname: names of countries
            iso3: ISO3 codes of countries

        """
        claimed_country, region = filename.split('.')[:2]
        if claimed_country in HMA_COUNTRY_RENAMES:
            iso3, cname = HMA_COUNTRY_RENAMES[claimed_country]
        else:
            # if country name has more than one capital letter, we must add a space.
            cname = self._put_space(claimed_country)
            iso3 = self._country_converter('STRING_TO_ISO3', cname)
        return cname + ' ' + region, iso3

    def _ipvanish_iso3_convertor(self, filename: str) -> str:
        """to convert countries' names to its ISO3 and names under the ipvanish vpn company

        Args:
            filename: the filename of a file containing countries name

        Returns:
            cname: names of countries
            iso3: ISO3 codes of countries

        """
        if (filename.split('-')[1] == 'UK'):
            cname = self._country_converter('ISO2_TO_STRING', 'GB')
            iso3 = 'GBR'
        else:
            cname = self._country_converter('ISO2_TO_STRING', filename.split('-')[1])
            cname = cname + ' ' + filename.split('-')[2]
            iso3 = self._country_converter('ISO2_TO_ISO3', filename.split('-')[1])

        return cname, iso3

    def _purevpn_iso3_convertor(self, filename: str) -> str:
        """to convert countries' ISO2 to their ISO3 and names under the purevpn company

        Args:
            filename: the filename of a file containing countries name

        Returns:
            cname: names of countries
            iso3: ISO3 codes of countries

        """
        iso2 = filename[:2].upper()
        if (iso2 == 'UK'):
            cname = self._country_converter('ISO2_TO_STRING', 'GB')
            iso3 = 'GBR'
        elif (iso2 == 'VL'):
            cname = self._country_converter('ISO2_TO_STRING', 'BE')
            iso3 = 'BEL'
        else:
            cname = self._country_converter('ISO2_TO_STRING', iso2)
            iso3 = self._country_converter('ISO2_TO_ISO3', iso2)
        return cname, iso3

    def _write_to_csv_file(self, vpn_info: str, path: str) -> None:
        """ Appends a line of data to specified .csv file

        Args:
            vpn_info: the information of vpn that will be written on the csv file
            path: the path where vpn info goes

        Returns:
            None

        """
        if path == None:
            logging.error("Could not write into csv file. csv file has not been initialized.")
            # erase later, put just for testing purposes.
            # print 'ERROR! No csv file.'
            sys.exit()
        else:
            message = [vpn_info['ip'], vpn_info['vpn_provider'],
                       vpn_info['hostname'], vpn_info['claimed_country_name'],
                       vpn_info['claimed_country_iso3'], vpn_info['path_to_config_file']]
            with open(path, 'a') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(message)
            return


    def _get_vpn_node_info(self, path_to_config: str, provider: str) -> None:
        """ Get vpn node configuration info from all .ovpn files in the specified directory. Push the extracted info into the .CSV file.

        Args:
            path_to_config: path to the directory containing all the .ovpn files
            provider: name of the vpn provider

        Returns:
            None

        """
        path_csv = self.path_to_config
        path_failed_csv = self.path_to_failed

        for filename in os.listdir(path_to_config):

            vpn_info = {'ip': None,
                        'vpn_provider': provider,
                        'hostname': None,
                        'claimed_country_name': None,
                        'claimed_country_iso3': None,
                        'path_to_config_file': None}

            # get iso3
            if (filename.endswith('.ovpn') and (provider == 'hma' or provider == 'ipvanish')) or \
                    (filename.endswith('tcp.ovpn') and provider == 'purevpn'):
                if provider == 'hma':
                    cname, iso3 = self._hma_iso3_convertor(filename)
                elif provider == 'ipvanish':
                    cname, iso3 = self._ipvanish_iso3_convertor(filename)
                elif provider == 'purevpn':
                    cname, iso3 = self._purevpn_iso3_convertor(filename)
                else:
                    logging.error("Invalid provider name. Aborting.")
                    sys.exit()

                vpn_info['claimed_country_name'] = cname
                vpn_info['claimed_country_iso3'] = iso3

                # TODO: check whether iso3 is correct

                # Obtain File Path.
                file_path = os.path.join(path_to_config, filename)
                vpn_info['path_to_config_file'] = file_path

                # Obtain URL
                with open(file_path, "r") as contents:
                    for ln in contents:
                        # exclusion of lines that start with remote- because purevpn config files
                        # have two lines that start with keyword 'remote'
                        if ((ln.startswith('remote')) and not (ln.startswith('remote-'))):
                            vpn_info['hostname'] = ln.split(' ')[1]

                # check if the url has been succesfully obtained:
                if vpn_info['hostname'] == None:
                    logging.error("Fatal Error. Could not find VPN Node from the .ovpn file.")
                    self._write_to_csv_file(vpn_info, path_failed_csv)
                    continue
                if vpn_info['claimed_country_iso3'] == None or vpn_info['claimed_country_iso3'] == '':
                    logging.error('ERROR: NO ISO3 PARAMETER PARSED FROM %s' % vpn_info['claimed_country_name'])
                    continue

                ip_addresses = self._get_ip_address(vpn_info['hostname'])
                if ip_addresses == 'FAILED':
                    self._write_to_csv_file(vpn_info, path_failed_csv)
                    continue

                oldPath = vpn_info['path_to_config_file']
                for ip in ip_addresses:
                    vpn_info['ip'] = ip
                    vpn_info['path_to_config_file'] = self._copy_ovpn_file_and_modify_hostname(
                        oldPath, vpn_info['vpn_provider'], vpn_info['hostname'], vpn_info['ip'])
                    self._write_to_csv_file(vpn_info, path_csv)
                os.remove(oldPath)

    def _download_save_to_file(self, URL: str, directory: str) -> None:
        """Download and save a file from an URL

        Args:
            URL: the URL contains the file
            directory: the path where you want this to happen

        Returns:
            None
        """
        urlretrieve(URL, directory)

    def _download_unzip_to_path(self, config_zip_url: str, zip_path: str, unzip_path: str) -> None:
        """Downlaod a zip file from a URL and extract it into a directory

        Args:
            config_zip_url: the URL with the zip file
            zip_path: the path that the zip is extracted to
            unzip_path: the path that the unzip file goes

        Returns:
            None

            """
        os.makedirs(unzip_path, exist_ok=True)
        logging.info("Downloading config .zip file")

        logging.info("Writing zip file into specified path: %s" % zip_path)

        # Copy a network object to a local file
        self._download_save_to_file(config_zip_url, zip_path)

        # extract all
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(unzip_path)

        # remove zip file
        os.remove(zip_path)

    def download_purevpn_config(self)->None:
        """Download purevpn config files

        Args:
            param directory: the path where you want this to happen

        Returns:
            None
        """
        pure_directory = os.path.join(self.directory, 'purevpn/')

        os.makedirs(pure_directory, exist_ok=True)

        # config_zip_url = "https://s3-us-west-1.amazonaws.com/heartbleed/windows/New+OVPN+Files.zip"
        # the link above doesn't work anymore
        config_zip_url= "https://d32d3g1fvkpl8y.cloudfront.net/heartbleed/windows/New+OVPN+Files.zip"
        zip_path = os.path.join(pure_directory, "../purevpn_config_files.zip")
        unzip_path = os.path.join(pure_directory, "unzipped")

        # Download and unzip config .zip file.
        self._download_unzip_to_path(config_zip_url, zip_path, unzip_path)

        # Copy ca and key to root path
        try:
            shutil.copyfile(os.path.join(unzip_path, 'New OVPN Files', 'ca.crt.crt'),
                            os.path.join(pure_directory, 'ca.crt'))
            shutil.copyfile(os.path.join(unzip_path, 'New OVPN Files', 'Wdc.key'),
                            os.path.join(pure_directory, 'Wdc.key'))

        except FileNotFoundError:
            # https://support.purevpn.com/command-line-setup-in-debian-linux
            logging.info("purevpn seems to have switched to embedding the keys in the .ovpn files")
            pass

        # parse all vpn node data into the CSV file.
        self._get_vpn_node_info(os.path.join(unzip_path, 'New OVPN Files/TCP'), 'purevpn')

        # remove all unzipped files:
        shutil.rmtree(os.path.join(unzip_path, 'New OVPN Files'))


    def parse_ipvanish_config(self, path_to_config: str)->None:
        """Replace "proto udp" with "proto tcp" in each ipvanish config file

          (for obelix server): parse config file and change "proto udp" --> "proto tcp"
          otherwise, we will get the following errors:
            "TLS Error: TLS key negotiation failed to occur within 60 seconds (check your network connectivity)"
            "TLS Error: TLS handshake failed"

            Args:
                path_to_config: path to the config files

            Returns:
                None

        """
        for filename in os.listdir(path_to_config):
            with open(os.path.join(path_to_config, filename), 'r') as f:
                texts = f.read()
                texts = texts.replace("proto udp", "proto tcp")
            with open(os.path.join(path_to_config, filename), 'w') as f:
                f.write(texts)

    def download_ipvanish_config(self)->None:
        """download the ipvanish config file and deal with errors

        Args:
            param directory: the path where you want this to happen

        Returns:
            None
        """
        ipvanish_directory = os.path.join(self.directory, 'ipvanish/')

        os.makedirs(ipvanish_directory, exist_ok=True)

        config_zip_url = "https://www.ipvanish.com/software/configs/configs.zip"
        zip_path = os.path.join(ipvanish_directory, "../ipvanish_config_files.zip")
        unzip_path = os.path.join(ipvanish_directory, "unzipped/TCP/")

        logging.info("Starting to download hma config file zip")

        # Download and unzip config .zip file.
        self._download_unzip_to_path(config_zip_url, zip_path, unzip_path)

        # copy crt and key to root path
        shutil.copyfile(os.path.join(unzip_path, 'ca.ipvanish.com.crt'),
                        os.path.join(ipvanish_directory, 'ca.ipvanish.com.crt'))

        # (for obelix server): parse config file and change "proto udp" --> "proto tcp"
        # otherwise, we will get the following errors:
        #   "TLS Error: TLS key negotiation failed to occur within 60 seconds (check your network connectivity)"
        #   "TLS Error: TLS handshake failed"
        self.parse_ipvanish_config(unzip_path)

        # parse all vpn node data into the CSV file.
        self._get_vpn_node_info(unzip_path, 'ipvanish')

        # remove all unzipped files:
        shutil.rmtree(unzip_path)


    def download_hma_configs(self)->None:
        """download the hma config files

        Args:
            param directory: the path where you want this to happen

        Returns:
            None
            
        """
        hma_directory = os.path.join(self.directory, 'hma')

        os.makedirs(hma_directory, exist_ok=True)

        config_zip_url = "https://hidemyass.com/vpn-config/vpn-configs.zip"
        zip_path = os.path.join(hma_directory, "../hma_config_files.zip")
        unzip_path = os.path.join(hma_directory, "unzipped/")

        ca_url = "https://vpn.hidemyass.com/vpn-config/keys/ca.crt"
        hmauserauth_url = "https://vpn.hidemyass.com/vpn-config/keys/hmauser.crt"
        hmauserkey_url = "https://vpn.hidemyass.com/vpn-config/keys/hmauser.key"

        logging.info("Starting to download hma config file zip")

        # Download and unzip config .zip file.
        self._download_unzip_to_path(config_zip_url, zip_path, unzip_path)

        # Download ca.crt and hmauser.key

        self._download_save_to_file(ca_url, os.path.join(hma_directory, 'ca.crt'))
        self._download_save_to_file(hmauserauth_url, os.path.join(hma_directory, 'hmauser_auth.key'))
        self._download_save_to_file(hmauserkey_url, os.path.join(hma_directory, 'hmauser.key'))

        # parse all vpn node data into the CSV file.
        self._get_vpn_node_info(os.path.join(unzip_path, 'TCP/'), 'hma')

        # remove directories
        shutil.rmtree(os.path.join(unzip_path, 'TCP'))
        shutil.rmtree(os.path.join(unzip_path, 'UDP'))
        shutil.rmtree(os.path.join(unzip_path, 'OpenVPN-2.4'))


    def _add_column_names_to_csv(self, path: str, names: list) -> None:
        """Add title of each column to the csv file

        Args:
            path: the path where csv sent to
            names: names on the top of the column

        Returns:
            None

        """
        with open(path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(names)


    def download(self) -> None:
        """Download the config file and parse the file into a new file

        Args:
            None

        Returns:
            None

        """

        os.makedirs(self.directory, exist_ok=True)

        # create csv files.
        names = ['ip', 'vpn_provider', 'hostname', 'claimed_country_name',
                 'claimed_country_iso3', 'path_to_config_file']
        self._add_column_names_to_csv(self.path_to_config, names)
        self._add_column_names_to_csv(self.path_to_failed, names)

        # get config files and parse .csv file.
        self.download_hma_configs()
        self.download_ipvanish_config()
        self.download_purevpn_config()


def download(config_path: str, fname_config: str, fname_failed: str) -> None:
    """Download the config files with vpn information

    Args:
        config_path: path to the config file
        fname_config: name of a csv file with vpn successful downloading
        fname_failed: name of a csv file with vpn fialed downloading

    Returns:
        None

    """
    DownloadVPNConfigs(config_path, fname_config, fname_failed).download()


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

    download(
        'configs/',
        'vpn_configs.csv',
        'vpn_configs_failed_downloading.csv'
    )
