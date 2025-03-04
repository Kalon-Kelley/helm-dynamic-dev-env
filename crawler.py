import csv
import random
import requests
import time

def random_time():
    return random.uniform(1,2)

num = 1000
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
    if 'dependencies' in obj['data']:
        chart_dependency[name] = len(obj['data']['dependencies'])
    else:
        chart_dependency[name] = 0

with open('dependency_data.csv', 'w', newline='') as f:
    field_names = ['repo_chart_name', 'dependency_count']
    writer = csv.DictWriter(f, fieldnames=field_names)

    writer.writeheader()
    for name in repo_chart_names:
        writer.writerow({'repo_chart_name': name, 'dependency_count': chart_dependency[name]})

end_time = time.time()
print(f'--- {end_time - start_time} seconds ---')

