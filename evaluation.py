import csv
import shutil
import subprocess
import time
import yaml

from pathlib import Path

# REPO_CHART_MAP = {
#     'https://kubernetes.github.io/dashboard': 'k8s-dashboard/kubernetes-dashboard',
#     'https://argoproj.github.io/argo-helm': 'argo/argo-cd',
#     'https://releases.rancher.com/server-charts/stable': 'rancher-stable/rancher',
#     'https://charts.jfrog.io': 'jfrog/artifactory',
# }
CHART_FILE = 'chart_name_url.csv'
WORKSPACE = '/charts'
RESULTS_FILE = 'results.csv'

def process_charts_and_evaluate(repo, chart):
    """ Pull helm repository and process helm chart to run evaluation on
    """
    chart_name = chart.split('/')[1]

    subprocess.run(f'helm repo add {chart.split("/")[0]} {repo}', shell=True, text=True)
    subprocess.run(f'helm pull {chart} --untar --destination {WORKSPACE}', shell=True, text=True)

    chart_yaml_path = Path(WORKSPACE) / chart_name / 'Chart.yaml'

    static_chart_path = Path(WORKSPACE) / f'{chart_name}_static'
    dynamic_chart_path = Path(WORKSPACE) / f'{chart_name}_dynamic'
    shutil.copytree(chart_yaml_path.parent, dynamic_chart_path)
    shutil.move(chart_yaml_path.parent, static_chart_path)

    # Add dynamic property to all dependencies
    with open(dynamic_chart_path / 'Chart.yaml', 'r') as f:
        chart_data = yaml.safe_load(f)
    if 'dependencies' in chart_data:
        for dep in chart_data['dependencies']:
            dep['dynamic'] = True
    with open(dynamic_chart_path / 'Chart.yaml', 'w') as f:
        yaml.dump(chart_data, f, default_flow_style=False)
    shutil.rmtree(dynamic_chart_path / 'charts', ignore_errors=True)
    shutil.rmtree(dynamic_chart_path / 'Chart.lock', ignore_errors=True)

    return static_chart_path, dynamic_chart_path

def get_chart_details(file):
    chart_map = dict()
    with open(file, newline='') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            chart_map[row['repo_url']] = row['repo_chart_name']
    return chart_map

def run_command_timed(cmd, path):
    """ Helper to calculate time taken to run a command
    """
    start_time = time.time()
    subprocess.run(cmd, shell=True, cwd=path, text=True)
    end_time = time.time()
    return end_time - start_time

def calculate_build_time_overhead(chart, static_chart_path, dynamic_chart_path):
    """ Calculate build time overhead
    """
    static_time = run_command_timed('helm package .', path=static_chart_path)
    dynamic_time = run_command_timed('helm-dyn package .', path=dynamic_chart_path)

    return {
        'Chart': chart,
        'Static build time (seconds)': static_time,
        'Dynamic build time (seconds)': dynamic_time,
        'Overhead (%)': ((static_time - dynamic_time) / static_time) * 100
    }

def calculate_package_size_overhead(chart, static_chart_path, dynamic_chart_path):
    """ Calculate package size overhead
    """
    print(static_chart_path)
    static_size = next(static_chart_path.glob('*.tgz'), None).stat().st_size
    dynamic_size = next(dynamic_chart_path.glob('*.tgz'), None).stat().st_size

    return {
        'Chart': chart,
        'Static package size (bytes)': static_size,
        'Dynamic package size (bytes)': dynamic_size,
        'Overhead (%)': ((static_size - dynamic_size) / static_size) * 100
    }

def cleanup(static_chart_path, dynamic_chart_path):
    shutil.rmtree(static_chart_path, ignore_errors=True)
    shutil.rmtree(dynamic_chart_path, ignore_errors=True)

def main():
    build_time_overhead_results = []
    package_size_results = []

    repo_chart_map = get_chart_details(CHART_FILE)

    for repo, chart in repo_chart_map.items():
        static_chart_path, dynamic_chart_path = process_charts_and_evaluate(repo, chart)
        
        # Evaluation 1: calculate build time overhead
        build_time_overhead_results.append(
            calculate_build_time_overhead(chart, static_chart_path, dynamic_chart_path)
        )

        # Evaluation 2: calculate package size overhead
        package_size_results.append(
            calculate_package_size_overhead(chart, static_chart_path, dynamic_chart_path)
        )

        cleanup(static_chart_path, dynamic_chart_path)

    with open(RESULTS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Chart', 'Static build time (seconds)', 'Dynamic build time (seconds)', 'Overhead (%)'])
        writer.writeheader()
        writer.writerows(build_time_overhead_results)

        writer = csv.DictWriter(f, fieldnames=['Chart', 'Static package size (bytes)', 'Dynamic package size (bytes)', 'Overhead (%)'])
        writer.writeheader()
        writer.writerows(package_size_results)

if __name__ == "__main__":
    main()
