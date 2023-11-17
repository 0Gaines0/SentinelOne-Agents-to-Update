import json
import requests
from pkg_resources import parse_version
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

tenant_name = ""
s1_base_url = ""
if not s1_base_url.endswith("/"):
    s1_base_url = "{}/".format(s1_base_url)
s1_token = ""
api_headers = {
    'Authorization': 'ApiToken {}'.format(s1_token),
    'Content-Type' : 'application/json',
}

get_packages_api_call = "{}web/api/v2.1/update/agent/packages".format(s1_base_url)
get_agent_url = "{}web/api/v2.1/agents".format(s1_base_url)

def get(url, params= {}):
    response = requests.get(url, headers=api_headers, params=params, verify=False)
    return response, response.json()

def get_device_list(cursor="", device_list=[], filter=[]):
    params_dict = {"cursor":cursor, "limit": 1000}
    if filter:
        params_dict.update(filter)
    _, response_data = get(get_agent_url, params=params_dict)
    device_data = response_data.get("data")
    if device_data:
        device_list.extend(device_data)
        next_cursor = response_data.get('pagination').get('nextCursor')
        if next_cursor:
            get_device_list(cursor=next_cursor, device_list=device_list)
    return device_list

def get_available_agent_packages(cursor="", package_list=[]):
    _, response_data = get(get_packages_api_call, params={"cursor":cursor, "limit": 1000})
    package_data = response_data.get("data")
    if package_data:
        package_list.extend(package_data)
        next_cursor = response_data.get('pagination').get('nextCursor')
        if next_cursor:
            get_available_agent_packages(cursor=next_cursor, package_list=package_list)
    return package_list

def get_acceptable_versions():
    acceptable_dict = {}
    package_list = get_available_agent_packages(cursor="", package_list=[])
    os_versions = list(set([current.get('osType') for current in package_list]))
    if os_versions:
        for os_name in os_versions:
            acceptable_dict.update({os_name:{}})
            os_package_list = [current for current in package_list if current.get('osType') == os_name]
            release_statuses = list(set([current.get('status') for current in os_package_list]))
            for release_statuses in release_statuses:
                os_package_release_status_list = [current for current in os_package_list if current.get('status')==release_statuses]
                package_version_list = list(set([current.get('version') for current in os_package_release_status_list]))
                package_version_list.sort(key=parse_version)
                if len(package_version_list) > 1:
                    n_version = package_version_list[-1]
                    n_2_version = package_version_list[-3]
                    acceptable_dict[os_name].update({release_statuses: {'n':n_version, 'n_2':n_2_version}})
                elif len(package_version_list) == 1:
                    n_version = package_version_list[-1]
                    acceptable_dict[os_name].update({release_statuses: {'n':n_version}})
    return acceptable_dict

def get_acceptable_versions_list():
    version_list =[]
    acceptable_dict = get_acceptable_versions()
    for _, version_dict in acceptable_dict.items():
        for _, n_version_dict in version_dict.items():
            for _, n_value in n_version_dict.items():
                version_list.append(n_value)
    return version_list

def get_latest_agent_versions():
    return_dict = {}
    acceptable_version_dict = get_acceptable_versions()
    package_list = get_available_agent_packages(cursor="", package_list=[])
    for os_version, version_dict in acceptable_version_dict.items():
        os_version_package_list = [current for current in package_list if version_dict.get('ga').get('n') == current.get('version')]
        package_name = os_version_package_list
        return_dict.update({os_version : package_name})
    return return_dict

def get_agents_to_update():
    all_devices_list = get_device_list(cursor="", device_list=[])
    acceptable_agent_versions = get_latest_agent_versions()
    agent_devices_to_upgrade_dict = {'devices' : {}, 'length': 0}
    for current in all_devices_list:
        device_id = current.get('computerName')
        if current.get('agentVersion') not in acceptable_agent_versions:
            device_info = {
                'computerName' : current.get('computerName'),
                'agentVersion' : current.get('agentVersion'),
                'osName' : current.get('osName')
            }
            agent_devices_to_upgrade_dict['devices'][device_id] = device_info
            agent_devices_to_upgrade_dict['length'] += 1

    return acceptable_agent_versions, agent_devices_to_upgrade_dict

agent_versions, agent_devices_to_upgrade_dict = get_agents_to_update()


print(json.dumps(agent_devices_to_upgrade_dict))

