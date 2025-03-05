import csv
import random
import requests
import time

# top number of helm charts to pull
num = 20

def random_time():
    return random.uniform(1,2)

start_time = time.time()
repo_chart_names = []

# get names of top {num} helm charts
off = 0
count = 0
while True:
    url = f'https://artifacthub.io/api/v1/packages/search?kind=0&facets=true&sort=relevance&limit=60&offset={off*60}'
    obj = requests.get(url).json()
    time.sleep(random_time())
    for package in obj['packages']:
        repo_name = package['repository']['name']
        chart_name = package['normalized_name']
        repo_chart_names.append(f'{repo_name}/{chart_name}')
        count += 1
        if count >= num:
            break
    if count >= num:
        break
    off += 1

# go through each url and count number of dependencies
chart_dependency = dict()
for name in repo_chart_names:
    url = f'https://artifacthub.io/api/v1/packages/helm/{name}'
    obj = requests.get(url).json()
    time.sleep(random_time())

    chart_info = dict()

    # count number of dependencies
    if 'dependencies' in obj['data']:
        chart_info['dep_count'] = len(obj['data']['dependencies'])
    else:
        chart_info['dep_count'] = 0
    
    # get repo url
    chart_info['repo_url'] = obj['repository']['url']

    # TODO: dependency chain? go to dependencies, do a total count
    # TODO: does dependency version matter?
    chart_dependency[name] = chart_info

with open('chart_info.csv', 'w', newline='') as f:
    field_names = ['repo_chart_name', 'dependency_count', 'repo_url']
    writer = csv.DictWriter(f, fieldnames=field_names)

    writer.writeheader()
    for name in repo_chart_names:
        writer.writerow({'repo_chart_name': name,
                         'dependency_count': chart_dependency[name]['dep_count'],
                         'repo_url': chart_dependency[name]['repo_url']})

end_time = time.time()
print(f'--- {end_time - start_time} seconds ---')
