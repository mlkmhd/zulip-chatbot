import requests
from config import *
import time
import zipfile


def trigger_gitlab_pipeline(topic_name, content):
    print("Triggering GitLab pipeline...")
    res = requests.post(GITLAB_BASE_URL + GITLAB_TRIGGER_URL, data={
        "token": GITLAB_TRIGGER_TOKEN,
        "ref": GITLAB_BRANCH,
        "variables[TOPIC_NAME]": topic_name,
        "variables[MESSAGE_CONTENT]": content
    })
    print("GitLab response:", res.text)
    pipeline_id = res.json().get("id")
    return pipeline_id

def get_result_from_pipeline(project_id, pipeline_id):

    counter = 0
    while counter < 10:
        response = requests.get(
            f"{GITLAB_BASE_URL}/api/v4/projects/{project_id}/pipelines/{pipeline_id}",
            headers= {
                "PRIVATE-TOKEN": GITLAB_API_TOKEN
            }
        )

        if response.status_code != 200:
            print("Failed to fetch pipeline status:", response.text)
            return "error", "failed to get the pipeline"

        status = response.json().get("status")
        print(f"Pipeline status: {status}")

        if status == "success":
            response = requests.get(
                f"{GITLAB_BASE_URL}/api/v4/projects/{project_id}/pipelines/{pipeline_id}/jobs",
                headers= {
                    "PRIVATE-TOKEN": GITLAB_API_TOKEN
                }
            )

            if response.status_code != 200:
                print("Failed to fetch jobs:", response.text)
                return "error", "failed to get the pipeline jobs"

            jobs = response.json()

            artifact_job = next((job for job in jobs if job.get("artifacts_file", {}).get("filename")), None)

            if not artifact_job:
                print("No job with artifacts found.")
                return "error", "failed to get the result from pipeline"

            job_id = artifact_job["id"]
            print(f"Found artifact job: {artifact_job['name']} (ID: {job_id})")

            artifacts_url = f"{GITLAB_BASE_URL}/api/v4/projects/{project_id}/jobs/{job_id}/artifacts"
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
                return "ok", content
            else:
                print("Failed to download artifacts:", artifact_response.text)
        elif status == "failed":
            return "error", "pipeline failed"

        time.sleep(10)
        counter+=1

    return "error"