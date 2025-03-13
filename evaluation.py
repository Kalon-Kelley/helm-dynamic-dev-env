import csv
import getpass
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

    if not Path(chart_yaml_path).exists():
        print(f'Skipping {repo} and {chart}: not found')
        return None, None

    static_chart_path = Path(WORKSPACE) / f'{chart_name}_static'
    dynamic_chart_path = Path(WORKSPACE) / f'{chart_name}_dynamic'
    shutil.copytree(chart_yaml_path.parent, dynamic_chart_path)
    shutil.move(chart_yaml_path.parent, static_chart_path)

    # Add dynamic property to all dependencies and increment version
    with open(dynamic_chart_path / 'Chart.yaml', 'r') as f:
        chart_data = yaml.safe_load(f)
    if 'dependencies' in chart_data:
        for dep in chart_data['dependencies']:
            dep['dynamic'] = True
    if 'version' in chart_data:
        static_version = chart_data['version']
        parts = chart_data['version'].split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        chart_data['version'] = '.'.join(parts)
        dynamic_version = chart_data['version']
    with open(dynamic_chart_path / 'Chart.yaml', 'w') as f:
        yaml.dump(chart_data, f, default_flow_style=False)
    shutil.rmtree(dynamic_chart_path / 'charts', ignore_errors=True)
    shutil.rmtree(dynamic_chart_path / 'Chart.lock', ignore_errors=True)

    return static_chart_path, dynamic_chart_path, static_version, dynamic_version

def get_chart_details(file):
    chart_map = dict()
    with open(file, newline='') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            chart_map[row['repo_url']] = row['repo_chart_name']
    return chart_map

def run_command_timed(cmd, path=None):
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
    static_package = next(static_chart_path.glob('*.tgz'), None)
    dynamic_package = next(dynamic_chart_path.glob('*.tgz'), None)

    if not static_package or not dynamic_package:
        print(f'Skipping {chart}: package files not found')
        return None

    static_size = static_package.stat().st_size
    dynamic_size = dynamic_package.stat().st_size

    return {
        'Chart': chart,
        'Static package size (bytes)': static_size,
        'Dynamic package size (bytes)': dynamic_size,
        'Overhead (%)': ((static_size - dynamic_size) / static_size) * 100
    }

def push_helm_chart_to_registry(helm_username, chart_path):
    """ Pushes a Helm chart tarball to a container registry
    """
    package = next(chart_path.glob('*.tgz'), None)

    if not package:
        print(f'Tarball not found in path {chart_path}')
        return None

    try:
        subprocess.run(f'helm push {str(chart_path / package)} oci://registry-1.docker.io/{helm_username}', check=True, shell=True)
        print(f'Successfully pushed {package}')
    except subprocess.CalledProcessError as e:
        print(f'Error pushing {package}: {e}')

def calculate_network_overhead(chart, helm_username, static_chart_path, dynamic_chart_path):
    """ Calculate network overhead aka pull time
    """
    static_package = next(static_chart_path.glob('*.tgz'), None)
    dynamic_package = next(dynamic_chart_path.glob('*.tgz'), None)

    if not static_package or not dynamic_package:
        print(f'Skipping as {chart} tarball not found')
        return None

    static_package = static_package.stem.rsplit('-', 1)
    dynamic_package = dynamic_package.stem.rsplit('-', 1)

    static_network_overhead = run_command_timed(f'helm pull oci://registry-1.docker.io/{helm_username}/{static_package[0]}:{static_package[1]}')
    dynamic_network_overhead = run_command_timed(f'helm-dyn pull oci://registry-1.docker.io/{helm_username}/{dynamic_package[0]}:{dynamic_package[1]}')

    return {
        'Chart': chart,
        'Static pull time (seconds)': static_network_overhead,
        'Dynamic pull time (seconds)': dynamic_network_overhead,
        'Overhead (%)': ((static_network_overhead - dynamic_network_overhead) / static_network_overhead) * 100
    }

def calculate_install_time(chart, static_chart_path, dynamic_chart_path):
    """ Calculate installation time of static and dynamic charts
    """
    subprocess.run('helm uninstall static-test', shell=True)
    subprocess.run('helm-dyn uninstall dynamic-test', shell=True)
    static_time = run_command_timed(f'helm install static-test {static_chart_path}')
    subprocess.run('helm uninstall static-test', shell=True)
    dynamic_time = run_command_timed(f'helm-dyn install dynamic-test {dynamic_chart_path}')
    subprocess.run('helm-dyn uninstall dynamic-test', shell=True)

    return {
        'Chart': chart,
        'Static install time (seconds)': static_time,
        'Dynamic install time (seconds)': dynamic_time,
        'Overhead (%)': ((dynamic_time - static_time) / static_time) * 100
    }

def calculate_cold_start_performance(chart, helm_username, static_version, dynamic_version):
    """ Calculate cold start performance using registry links
    """
    static_name = chart.split('/')[1]
    dynamic_name = chart.split('/')[1]

    subprocess.run('helm uninstall static-test', shell=True)
    subprocess.run('helm-dyn uninstall dynamic-test', shell=True)
    static_registry_link = f'oci://registry-1.docker.io/{helm_username}/{static_name}:{static_version}'
    dynamic_registry_link = f'oci://registry-1.docker.io/{helm_username}/{dynamic_name}:{dynamic_version}'
    static_time = run_command_timed(f'helm install static-test {static_registry_link}')
    subprocess.run('helm uninstall static-test', shell=True)
    dynamic_time = run_command_timed(f'helm-dyn install dynamic-test {dynamic_registry_link}')
    subprocess.run('helm-dyn uninstall dynamic-test', shell=True)

    return {
        'Chart': chart,
        'Static cold start (seconds)': static_time,
        'Dynamic cold start (seconds)': dynamic_time,
        'Overhead (%)': ((dynamic_time - static_time) / static_time) * 100
    }

def cleanup(static_chart_path, dynamic_chart_path):
    shutil.rmtree(static_chart_path, ignore_errors=True)
    shutil.rmtree(dynamic_chart_path, ignore_errors=True)
    subprocess.run(f'rm {WORKSPACE}/*.tgz', shell=True)

def main():
    build_time_overhead_results = []
    package_size_results = []
    network_overhead_results = []
    install_time_results = []
    cold_start_performance_results = []

    repo_chart_map = get_chart_details(CHART_FILE)

    docker_username = input('Docker username: ')
    docker_password = getpass.getpass('Docker password: ')
    subprocess.run(
        f'docker login -u {docker_username} --password-stdin',
        input=docker_password.encode(),
        check=True,
        shell=True
    )

    helm_username = input('Helm username: ')
    helm_password = getpass.getpass('Helm password: ')
    subprocess.run(
        f'helm registry login registry-1.docker.io -u {helm_username} --password-stdin',
        input=helm_password.encode(),
        check=True,
        shell=True
    )

    for repo, chart in repo_chart_map.items():
        try:
            static_chart_path, dynamic_chart_path, static_version, dynamic_version = process_charts_and_evaluate(repo, chart)

            if static_chart_path and dynamic_chart_path:
                # Evaluation 1: calculate build time overhead
                build_time_overhead_results.append(
                    calculate_build_time_overhead(chart, static_chart_path, dynamic_chart_path)
                )

                # Push packages to registry
                push_helm_chart_to_registry(helm_username, static_chart_path)
                push_helm_chart_to_registry(helm_username, dynamic_chart_path)

                # Evaluation 2: calculate package size overhead
                package_size_result = calculate_package_size_overhead(chart, static_chart_path, dynamic_chart_path)
                if package_size_result:
                    package_size_results.append(package_size_result)

                # Evaluation 3: calculate network traffic overhead aka time taken to pull the charts
                network_overhead_results.append(
                    calculate_network_overhead(chart, helm_username, static_chart_path, dynamic_chart_path)
                )

                # Evaluation 4: calculate install time of the tarball pulled in the previous step
                install_time_results.append(
                    calculate_install_time(chart, static_chart_path, dynamic_chart_path)
                )

                # Evaluation 5: cold start performance aka time taken to install directly from the registry
                cold_start_performance_results.append(
                    calculate_cold_start_performance(chart, helm_username, static_version, dynamic_version)
                )

                cleanup(static_chart_path, dynamic_chart_path)

                # Write to CSV after each iteration
                with open(RESULTS_FILE, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['Chart', 'Static build time (seconds)', 'Dynamic build time (seconds)', 'Overhead (%)'])
                    writer.writeheader()
                    writer.writerows(build_time_overhead_results)

                    writer = csv.DictWriter(f, fieldnames=['Chart', 'Static package size (bytes)', 'Dynamic package size (bytes)', 'Overhead (%)'])
                    writer.writeheader()
                    writer.writerows(package_size_results)

                    writer = csv.DictWriter(f, fieldnames=['Chart', 'Static pull time (seconds)', 'Dynamic pull time (seconds)', 'Overhead (%)'])
                    writer.writeheader()
                    writer.writerows(network_overhead_results)

                    writer = csv.DictWriter(f, fieldnames=['Chart', 'Static install time (seconds)', 'Dynamic install time (seconds)', 'Overhead (%)'])
                    writer.writeheader()
                    writer.writerows(install_time_results)

                    writer = csv.DictWriter(f, fieldnames=['Chart', 'Static cold start (seconds)', 'Dynamic cold start (seconds)', 'Overhead (%)'])
                    writer.writeheader()
                    writer.writerows(cold_start_performance_results)

        except:
            continue


if __name__ == "__main__":
    main()
