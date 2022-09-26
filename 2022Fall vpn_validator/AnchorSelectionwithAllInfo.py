import csv


with open('../../py1/2022Fall vpn_validator/all_abbrev.csv', mode='r') as infile:
    reader = csv.reader(infile)
    mydict = {rows[1]:rows[2] for rows in reader}

# part 1
# create a new csv file with the new column country
# with open('anchorSelection.csv','r') as csvinput:
#     with open('anchorSelectionContinents.csv', 'w') as csvoutput:
#         writer = csv.writer(csvoutput, lineterminator='\n')
#         reader = csv.reader(csvinput)
#
#         all = []
#         header = next(reader)
#
#         for row in reader:
#
#             row.append(mydict[row[7]])
#             all.append(row)
#
#         writer.writerow(header + ["continents"])
#         writer.writerows(all)

# import geopy.distance

#part 2
#calculate the distance from each anchor the the continent it sits
# with open('anchorSelectionContinents.csv','r') as csvinput:
#     with open('anchorSelectionContinentsDistance.csv', 'w') as csvoutput:
#         writer = csv.writer(csvoutput, lineterminator='\n')
#         reader = csv.reader(csvinput)
#
#         all = []
#         header = next(reader)
#         for row in reader:
#             coords_1 = (row[5], row[4])
#             loc = row[9]
#             if loc=="Asia":
#                 #          lat         lon
#                 coords_2 = (43.6805556,87.3311)
#             elif loc == "South America":
#                 coords_2 = (-8.7832,-55.4915)
#             elif loc== "North America":
#                 coords_2 =(54.5260,-105.2551)
#             elif loc == "Europe":
#                 coords_2 = (54.5260,25.3191)
#             elif loc =="Oceania":
#                 coords_2 = (-25.2744,133.7751)
#             elif loc == "Africa":
#                 coords_2 = (1.261,16.942)
#             else:
#                  print("debug")
#             distance = geopy.distance.geodesic(coords_1, coords_2).km
#             row.append(distance)
#             all.append(row)
#
#         writer.writerow(header + ["distance to continent center"])
#         writer.writerows(all)

#part 3
#use beautiful soup to extract the data of all time coonnection
import requests
import re
from bs4 import BeautifulSoup
with open('anchorSelection.csv','r') as csvinput:
    with open('anchorSelectionAll.csv', 'w') as csvoutput:
        writer = csv.writer(csvoutput, lineterminator='\n')
        reader = csv.reader(csvinput)

        all = []
        header = next(reader)
        n=1
        URLtest = "https://atlas.ripe.net/frames/probes/6610/"
        page = requests.get(URLtest)
        soup = BeautifulSoup(page.content, "html.parser")
        table = soup.find('table', {"class": "resolutions table table-condensed"})
        list = table.find_all(text=re.compile("%"))
        sign = soup.find_all(text=re.compile("Still Connected"))
        table_1 = soup.find("table", {"class": "table table-condensed table-striped table-hover"})
        Anchor_ping = table_1.find(text=re.compile("anchors"))
        if Anchor_ping == []:
            Anchor_ping = Anchor_ping.replace('(', '').replace(')', '').replace("anchors", "")
            print(Anchor_ping)
        else:
            print("empty")
            Anchor_ping = Anchor_ping


        table_2 = soup.find_all("table", {"class": "table table-condensed table-striped table-hover"})[1]
        Probes_ping = table_2.find_all(text=re.compile("probes"))

        if Probes_ping == []:
            print("empty")
            Probes_ping = Probes_ping
        else:
            Probes_ping = Probes_ping[0].replace('(', '').replace(')', '').replace("probes", "")
            print(Anchor_ping)



        # for row in reader:
        #     URL = "https://atlas.ripe.net/frames/probes/"+row[2]+"/"
        #     page = requests.get(URL)
        #     soup = BeautifulSoup(page.content, "html.parser")
        #     #extract the All Time connection percentage
        #     table = soup.find('table', {"class": "resolutions table table-condensed"})
        #     list = table.find_all(text=re.compile("%"))
        #     #search if there is "Still Connected" in the frame code
        #     sign = soup.find_all(text=re.compile("Still Connected"))
        #     if sign == []:
        #         row.append("Not Connected")
        #     else:
        #         row.append("Connected")
        #
        #     #extract the ping info
        #     table_1 = soup.find("table", {"class": "table table-condensed table-striped table-hover"})
        #     Anchor_ping = table_1.find(text=re.compile("anchors"))
        #
        #     if Anchor_ping == []:
        #         print("Empty" + Anchor_ping)
        #         Anchor_ping = []
        #     else:
        #         Anchor_ping = Anchor_ping.replace('(', '').replace(')', '').replace("anchors", "")
        #
        #     table_2 = soup.find_all("table", {"class": "table table-condensed table-striped table-hover"})[1]
        #     Probes_ping = table_2.find_all(text=re.compile("probes"))
        #
        #     if Probes_ping == []:
        #         print("Empty" + Probes_ping)
        #         Probes_ping = []
        #     else:
        #         Probes_ping = Probes_ping[0].replace('(', '').replace(')', '').replace("probes", "")

                # label the progress
            # print(row.append(list[-1]))

            # row.append(Anchor_ping)
            # row.append(Probes_ping)
            # all.append(row)
            # # print(n, row)
            # n = n + 1



        writer.writerow(header + ["All Time"]+["Status"]+["anchors p"]+["probes p"])
        writer.writerows(all)


