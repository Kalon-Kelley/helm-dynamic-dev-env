import csv
import random
import requests
import time

# top number of helm charts to pull
NUM = 100

def random_time():
    return random.uniform(1,2)

start_time = time.time()
repo_chart_names = []

# get names of top {NUM} helm charts
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
        if count >= NUM:
            break
    if count >= NUM:
        break
    off += 1

print(f'retrieved top {NUM} charts, crawling through each chart...')

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

print('finished crawling, creating output files...')

# create csv for evaluation script
with open('chart_name_url.csv', 'w', newline='') as f:
    field_names = ['repo_chart_name', 'repo_url']
    writer = csv.DictWriter(f, fieldnames=field_names)

    writer.writeheader()
    for name in repo_chart_names:
        writer.writerow({'repo_chart_name': name,
                         'repo_url': chart_dependency[name]['repo_url']})

# create csv for dependency stats
with open('chart_dependency.csv', 'w', newline='') as f:
    field_names = ['repo_chart_name', 'total_dependency_count']
    writer = csv.DictWriter(f, fieldnames=field_names)

    writer.writeheader()
    for name in repo_chart_names:
        writer.writerow({'repo_chart_name': name,
                         'total_dependency_count': chart_dependency[name]['dep_count']})

print('finished creating output files!')
end_time = time.time()
print(f'--- {end_time - start_time} seconds ---')
