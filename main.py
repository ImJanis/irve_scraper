import requests
import shutil
from pykml import parser
import json
import os
import datetime as dt
import argparse

from config import API_URL, ASSETS_URL

def download_file(url):
    temp_dirpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    temp_filepath = os.path.join(temp_dirpath, url.split('/')[-1])
    temp_filepath = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(temp_filepath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    return temp_filepath

def list_files(dirpath):
    files = [os.path.join(dirpath, f) for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f)) and f.endswith('.json') and f.startswith('corresp_data_')]
    return files

def get_mostest_recent_file():
    files = list_files(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
    sorted_files = sorted(files, key=lambda x: dt.datetime.strptime(x.split('/')[-1].split('_')[2] + '_' + x.split('/')[-1].split('_')[3].split(' ')[0].split('.')[0], "%Y-%m-%d_%H-%M-%S"))
    return sorted_files[-1]

def get_partial_corresps_data(assets_url):
    #download assets
    local_filename = download_file(assets_url)
    doc = parser.parse(local_filename).getroot()

    partial_corresps_data = []
    for placemark in doc.Document.Placemark:
        corresp_id = int(placemark.ExtendedData.Data[0].value.text)
        point = placemark.Point.coordinates.text
        partial_corresps_data.append({'corresp_id': corresp_id, 'coordinates': {'lat': point.split(',')[1], 'lon': point.split(',')[0]}})
    return partial_corresps_data

def get_complete_corresps_data(partial_corresps_data, only_new=False):
    if only_new: #get only new corresps
        cheked_filepath = get_mostest_recent_file()
        with open(cheked_filepath, 'r', encoding='utf-8') as f:
            check_data = json.load(f)
        missing_partial_corresps_data = []
        for i in range(len(partial_corresps_data)):
            query_corresp_id = partial_corresps_data[i]['corresp_id']
            #check if corresp_id not in check_data
            if not any(checked_corresp['corresp_id'] == query_corresp_id for checked_corresp in check_data):
                missing_partial_corresps_data.append(partial_corresps_data[i])
                print('New corresp_id : {}'.format(query_corresp_id))
        if len(missing_partial_corresps_data) > 0:
            print('\nFound {} new corresps'.format(len(missing_partial_corresps_data)))
        searching_corresps_data = missing_partial_corresps_data
    else: #get all corresps
        searching_corresps_data = partial_corresps_data

    #get complete data
    print(f'\nGetting data for {len(searching_corresps_data)} corresps...\n----------------')
    corresps_complete_data = []
    for i in range(len(searching_corresps_data)):
        corresp_id = searching_corresps_data[i]['corresp_id']
        r = requests.post(API_URL, json={"corresp_id": int(corresp_id)})
        r_mess = r.json()["message"]
        r_mess.update({'corresp_id': corresp_id})
        r_mess.update({'coordinates': searching_corresps_data[i]['coordinates']})
        corresps_complete_data.append(r_mess)
        print(f'Found {r_mess["name"]} with id {corresp_id}, {i+1}/{len(searching_corresps_data)}, {round(i/len(searching_corresps_data)*100,2)}%')

    if only_new: #add new data to old data
        corresps_complete_data = check_data + corresps_complete_data

    #save data
    filename = 'corresp_data_{}.json'.format(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    with open(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'), filename), 'w', encoding='utf-8') as f:
        json.dump(corresps_complete_data, f, ensure_ascii=False, indent=4)

    if only_new:
        print(f'----------------\nSaved {len(corresps_complete_data)} corresps (new: {len(missing_partial_corresps_data)}) to {filename}')

    return corresps_complete_data

def main(only_new=False):
    partial_corresps_data = get_partial_corresps_data(ASSETS_URL)
    corresps_complete_data = get_complete_corresps_data(partial_corresps_data, only_new=only_new)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()

    # Adding optional argument
    argparser.add_argument("-on", "--onlynew", help = "Only scrap new corresps", action='store_true')

    # Read arguments from command line
    args = argparser.parse_args()

    # Check for --onlynew
    if args.onlynew:
        main(only_new=True)
    else:
        main()