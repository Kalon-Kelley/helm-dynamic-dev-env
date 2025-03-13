import csv
import random
import requests
import time

# top number of helm charts to pull
NUM = 10

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
visited_chart_info = dict()

def visit_chart(name):
    if name in visited_chart_info:
        return visited_chart_info[name]

    url = f'https://artifacthub.io/api/v1/packages/helm/{name}'
    obj = requests.get(url).json()
    time.sleep(random_time())

    chart_info = dict()

    # count number of dependencies
    if 'dependencies' in obj['data']:
        chart_info['first_layer_dep_count'] = len(obj['data']['dependencies'])
        chart_info['num_layers_below'] = 1
        chart_info['total_dep_count'] = chart_info['first_layer_dep_count']
        for dep in obj['data']['dependencies']:
            if 'artifacthub_repository_name' in dep:
                dep_name = f"{dep['artifacthub_repository_name']}/{dep['name']}"
                dep_chart_info = visit_chart(dep_name)
                chart_info['num_layers_below'] = max(chart_info['num_layers_below'], dep_chart_info['num_layers_below'] + 1)
                chart_info['total_dep_count'] += dep_chart_info['total_dep_count']
    else:
        chart_info['first_layer_dep_count'] = 0
        chart_info['num_layers_below'] = 0
        chart_info['total_dep_count'] = 0
    
    # get repo url
    chart_info['repo_url'] = obj['repository']['url']

    visited_chart_info[name] = chart_info
    return visited_chart_info[name]

for name in repo_chart_names:
    chart_dependency[name] = visit_chart(name)

print(chart_dependency)
print()
print(visited_chart_info)

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
with open('chart_dependency_stats.csv', 'w', newline='') as f:
    field_names = ['repo_chart_name', 'first_layer_dep_count', 'num_layers_below', 'total_dep_count']
    writer = csv.DictWriter(f, fieldnames=field_names)

    writer.writeheader()
    for name in repo_chart_names:
        writer.writerow({'repo_chart_name': name,
                         'first_layer_dep_count': chart_dependency[name]['first_layer_dep_count'],
                         'num_layers_below': chart_dependency[name]['num_layers_below'],
                         'total_dep_count': chart_dependency[name]['total_dep_count']})

print('finished creating output files!')
end_time = time.time()
print(f'--- {end_time - start_time} seconds ---')
