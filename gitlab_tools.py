import requests
from config import *
import time
import zipfile
import logging
import yaml
import urllib
import tempfile
import os
import subprocess

logger = logging.getLogger(__name__)

def update_project_version(project_path, new_version):
    # config
    repo_url = f"https://oauth2:{ GITLAB_API_TOKEN }@{ GITLAB_BASE_DOMAIN }/{ project_path }"
    clone_dir = "/tmp/myrepo"
    file_path = "version"

    subprocess.run(["git", "clone", repo_url, clone_dir], check=True)

    full_path = os.path.join(clone_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(new_version)

    subprocess.run(["git", "add", file_path], cwd=clone_dir, check=True)
    subprocess.run(["git", "commit", "-m", "update version file"], cwd=clone_dir)

    subprocess.run(["git", "push", "origin", "HEAD"], cwd=clone_dir)
    print("Pushed successfully")

def trigger_gitlab_pipeline(project_path, trigger_token, variables):
    print("Triggering GitLab pipeline...")
    data= {
        "token": trigger_token,
        "ref": GITLAB_BRANCH
    }
    if variables:
        for key, value in variables.items():
            data["variables[" + key + "]"] = value
    encoded_project_path = urllib.parse.quote_plus(project_path)
    res = requests.post(GITLAB_BASE_URL + "/api/v4/projects/" + encoded_project_path + "/trigger/pipeline", data=data)
    print("GitLab response:", res.text)
    return res

def get_result_from_pipeline(project_path, pipeline_id):
    encoded_project_path = urllib.parse.quote_plus(project_path)
    counter = 0
    while counter < 20:
        response = requests.get(
            f"{GITLAB_BASE_URL}/api/v4/projects/{encoded_project_path}/pipelines/{pipeline_id}",
            headers= {
                "PRIVATE-TOKEN": GITLAB_REPLICATE_PACKAGE_API_TOKEN
            }
        )

        if response.status_code != 200:
            print("Failed to fetch pipeline status:", response.text)
            return "error", "failed to get the pipeline"

        status = response.json().get("status")
        print(f"Pipeline status: {status}")

        if status == "success":
            result = get_artifacts_result(project_path, pipeline_id)
            return "success", result
        elif status == "failed":
            result = get_artifacts_result(project_path, pipeline_id)
            return "error", result

        time.sleep(10)
        counter+=1

    return "error", "pipeline did not finish in time"

def get_artifacts_result(project_path, pipeline_id):
    encoded_project_path = urllib.parse.quote_plus(project_path)
    response = requests.get(
        f"{GITLAB_BASE_URL}/api/v4/projects/{encoded_project_path}/pipelines/{pipeline_id}/jobs",
        headers= {
            "PRIVATE-TOKEN": GITLAB_API_TOKEN
        }
    )

    if response.status_code != 200:
        print("Failed to fetch jobs:", response.text)
        return "error", "failed to get the pipeline jobs"

    jobs = response.json()

    artifact_job = next((job for job in jobs if job.get("artifacts_file", {}).get("filename")), None)

    if artifact_job:

        job_id = artifact_job["id"]
        print(f"Found artifact job: {artifact_job['name']} (ID: {job_id})")

        artifacts_url = f"{GITLAB_BASE_URL}/api/v4/projects/{encoded_project_path}/jobs/{job_id}/artifacts"
        artifact_file_path = "data/result.zip"

        artifact_response = requests.get(
            artifacts_url,
            headers= {
                "PRIVATE-TOKEN": GITLAB_API_TOKEN
            },
            stream=True
        )

        if artifact_response.status_code == 200:
            os.makedirs("data", exist_ok=True)
            with open(artifact_file_path, 'wb') as f:
                for chunk in artifact_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Artifacts downloaded to {artifact_file_path}")

            with zipfile.ZipFile(artifact_file_path, 'r') as zip_ref:
                zip_ref.extractall("data")
            with open("data/result.txt", "r", encoding="utf-8") as f:
                content = f.read()
            return content
        else:
            print("Failed to download artifacts:", artifact_response.text)

def get_project_environments(project_name):
    """Returns all environment paths where project exists"""
    try:
        env_paths = []
        headers = {"PRIVATE-TOKEN": GITLAB_API_TOKEN}

        # Get all environment groups (dev, sandbox, etc.)
        envs = requests.get(
            f"{GITLAB_API_V4_URL}/groups/{GITLAB_CD_GROUP_ID}/subgroups",
            headers=headers,
            params={"per_page": 100},
            timeout=10
        ).json()

        # Check each environment group
        for env in envs:
            # Get ALL projects in this environment (including nested subgroups)
            projects = requests.get(
                f"{GITLAB_API_V4_URL}/groups/{env['id']}/projects",
                headers=headers,
                params={
                    "include_subgroups": "true",  # 👈 Key parameter
                    "search": project_name,
                    "per_page": 100
                },
                timeout=15
            ).json()

            # Find matching projects and record their full paths
            for proj in projects:
                if proj['name'] == project_name and "old" not in proj['path_with_namespace']:
                    # Extract path components: devops/CD/<env>/<subgroup>/...
                    encoded_project_path = urllib.parse.quote_plus(proj['path_with_namespace'])
                    repository_file_tree = requests.get(
                        f"{GITLAB_API_V4_URL}/projects/{encoded_project_path}/repository/tree",
                        headers=headers,
                        params={"recursive": "true", "ref": "main"},
                        timeout=15
                    ).json()

                    cluster_namespaces = set()
                    for item in repository_file_tree:
                        path = item.get('path', '')
                        parts = path.split('/')
                        # Match paths with at least two directory levels
                        if len(parts) >= 2 and all(parts[:2]):
                            cluster_namespaces.add(f"{parts[0]}/{parts[1]}")

                    for cluster_namespace in cluster_namespaces:
                        encoded_file_path = urllib.parse.quote_plus(cluster_namespace +"/version")
                        version = requests.get(
                            f"{GITLAB_API_V4_URL}/projects/{encoded_project_path}/repository/files/{encoded_file_path}/raw?ref={proj['default_branch']}",
                            headers=headers,
                            timeout=15
                        ).text.strip()

                        encoded_file_path = urllib.parse.quote_plus(cluster_namespace +"/config/values.yaml")
                        nodeports = []
                        values_yaml_response = requests.get(
                            f"{GITLAB_API_V4_URL}/projects/{encoded_project_path}/repository/files/{encoded_file_path}/raw?ref={proj['default_branch']}",
                            headers=headers,
                            timeout=15
                        )

                        if values_yaml_response.ok:
                            values = yaml.safe_load(values_yaml_response.text)
                            valid_keys = {"ports", "port", "nodeport", "nodeports"}

                            def walk(node, path=None):
                                if path is None:
                                    path = []
                                if 'network-policy' in path:
                                    return

                                if isinstance(node, dict):
                                    for k, v in node.items():
                                        full_path = path + [k]

                                        if k.lower() in valid_keys:
                                            port_block = v

                                            if isinstance(port_block, dict):
                                                for subkey, val in port_block.items():
                                                    if isinstance(val, int) and 30000 <= val <= 32767:
                                                        nodeports.append({"port-name": subkey, "port-number": val})
                                            elif isinstance(port_block, int) and 30000 <= port_block <= 32767:
                                                nodeports.append({"port-name": "unknown", "port-number": port_block})

                                        walk(v, full_path)

                                elif isinstance(node, list):
                                    for i, item in enumerate(node):
                                        full_path = path + [str(i)]
                                        walk(item, full_path)

                            walk(values)

                        env_paths.append(
                            [
                                f"{cluster_namespace}",
                                proj['web_url'],
                                version,
                                nodeports
                            ]
                        )

        return sorted(env_paths) if env_paths else []

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None

def search_for_config(project_sub_path, search_key):
    project_encoded = urllib.parse.quote_plus("devops/CD/" + project_sub_path)
    url = f"{GITLAB_BASE_URL}/api/v4/projects/{project_encoded}/repository/archive.zip"
    params = {"sha": "main"}
    headers = {"PRIVATE-TOKEN": GITLAB_API_TOKEN}

    matched_files = []

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "repo.zip")

        print(f"Downloading to: {zip_path}")
        r = requests.get(url, headers=headers, params=params)
        if not r.ok:
            print(f"Failed to download zip: {r.status_code}")
            exit(1)

        with open(zip_path, "wb") as f:
            f.write(r.content)

        # === STEP 2: Extract ZIP ===
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # === STEP 3: Recursively search for SEARCH_TERM ===
        zip_root_dir = None
        for name in os.listdir(temp_dir):
            full_path = os.path.join(temp_dir, name)
            if os.path.isdir(full_path):
                zip_root_dir = full_path
                break

        if not zip_root_dir:
            print("Could not find extracted project directory.")
            return

        for root, dirs, files in os.walk(zip_root_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        matching_lines = [
                            line.strip() for line in lines if search_key in line
                        ]
                        if matching_lines:
                            rel_path = os.path.relpath(file_path, zip_root_dir)
                            if rel_path.startswith("config") and not rel_path.startswith("defaults/"):
                                matched_files.append((rel_path.replace('config/', ''), matching_lines))
                except Exception:
                    continue

    return matched_files