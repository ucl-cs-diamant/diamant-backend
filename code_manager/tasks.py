from celery import shared_task
# import concurrent.futures

from django.core.files import File
from game_engine.models import User, UserCode

from git import Repo
import os
import requests
import tempfile
import re
import tarfile


def list_classroom_repos(access_token, organization, prefix, params=None):
    if access_token is None:
        raise ValueError("Invalid access token.")
    if params is None:
        params = {'per_page': 100}

    org_repos = list()
    url = f"https://api.github.com/orgs/{organization}/repos"
    headers = {'Accept': "application/vnd.github.v3+json",
               'Authorization': f"token {access_token}", }

    # Users of the language are advised to use the while-True form with an inner
    # if-break when a do-while loop would have been appropriate.  PEP315
    while True:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        org_repos.extend(res.json())

        if (next_url := res.links.get("next", None)) is None:
            break
        url = next_url['url']

    classroom_repos = []
    for org_repo in org_repos:
        if (org_repo.get("name", "")).startswith(prefix):
            classroom_repos.append(org_repo)

    return classroom_repos


def check_identity(file_path):
    with open(file_path, 'r') as identity_file:
        identity_data = identity_file.readlines()
        email = None
        student_num = None
        for line in identity_data:  # todo: this seems hacky. To improve?
            if "Email address:" in line:
                email = line[14:].strip()
                if " " in email or not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
                    # print(f"rejecting email {email}")
                    return None
                continue
            if "Student number:" in line:
                student_num = line[15:]
                try:
                    student_num = int(student_num)
                except (ValueError, TypeError):
                    # print(f"rejecting student number {student_num}")
                    return None
                continue

        if email is not None and student_num is not None:
            return student_num, email
        return None


def create_user(student_id, student_email, github_username):
    # get_or_create should be redundant, but it never hurts to be cautious?
    student_object, created = User.objects.get_or_create(email_address=student_email,
                                                         student_id=student_id,
                                                         github_username=github_username)
    if not created:
        student_object.student_id = student_id
        student_object.student_email = student_email
        student_object.github_username = github_username
        student_object.save()


def clone_repo(repo_url: str, destination: str) -> Repo:
    # cloning of private repository possible by providing <username>:<personal access token> pair
    # use https://<username>:<personal access token>@github.com/repo_owner/repo_name
    auth_url_string = f"{os.environ['GITHUB_API_TOKEN_USER']}:{os.environ.get('GITHUB_API_TOKEN')}@github.com/".join(
        # repo["clone_url"].split("github.com/")
        repo_url.split("github.com/")
    )
    repo = Repo.clone_from(auth_url_string, destination)
    return repo


@shared_task
def fetch_user_authorization():
    prefix = "test-assignment-"
    repos = list_classroom_repos(os.environ.get("GITHUB_API_TOKEN"), "ucl-cs-diamant", prefix=prefix)
    for repo in repos:
        username = repo["name"][len(prefix):]
        if not User.objects.filter(github_username=username).exists():
            # if user not exist, clone repo, scan for ID, and create User
            with tempfile.TemporaryDirectory() as temp_dir:
                clone_repo(repo["clone_url"], temp_dir)

                # todo: ####  ADD A TOKEN CHECK, USERS WILL BE PRE-GENERATED INSTEAD OF BEING CREATED HERE ####
                for path in os.listdir(temp_dir):
                    path = os.path.join(temp_dir, path)
                    if os.path.isfile(path) and os.stat(path).st_size < 1024:  # skip over large files
                        # todo: verify correctness. written with very little sleep
                        if (identity := check_identity(path)) is not None:
                            student_id, student_email = identity
                            create_user(student_id, student_email, username)
                            # print(f"Created user: {student_id} - {username}")
                            break  # breaks inner loop, resumes outer loop


@shared_task
def clone_repositories():
    # github_api_token = os.environ.get('GITHUB_API_TOKEN', None)
    # if github_api_token is None:
    #     raise ValueError("No Github API token provided.")
    # todo: change org and prefix, move to environment file/environment variables
    # prefix = "test-sample-code-"
    # repos = list_classroom_repos(github_api_token, "ucl-cs-diamant", prefix)
    prefix = "test-sample-code-"
    repos = list_classroom_repos(os.environ.get("GITHUB_API_TOKEN"), "ucl-cs-diamant", prefix=prefix)
    for repo in repos:
        username = repo["name"][len(prefix):]
        if User.objects.filter(github_username=username).exists():
            user_instance = User.objects.get(github_username=username)
            # if user exists, clone repo and tar directory (otherwise wait until their user instance is created)
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_instance = clone_repo(repo["clone_url"], temp_dir)
                latest_main_commit_datetime = repo_instance.head.reference.commit.committed_datetime

                code_inst, created = UserCode.objects.get_or_create(user=user_instance,
                                                                    commit_time=latest_main_commit_datetime)
                if created:
                    with tempfile.TemporaryFile() as temp_file:
                        with tarfile.open(fileobj=temp_file, mode="w") as tar_out:
                            for dir_entry in os.listdir(temp_dir):
                                # arcname removes temp_dir prefix from tar
                                tar_out.add(os.path.join(temp_dir, dir_entry), arcname=dir_entry)
                        code_inst.source_code.save(f"{repo['name']}-{repo_instance.head.reference.commit.hexsha}.tar",
                                                   File(temp_file))
                    if UserCode.objects.filter(user=user_instance, is_latest=True).count() > 1:
                        last_latest = UserCode.objects.filter(user=user_instance, is_latest=True)[1:]
                        for elem in last_latest:    # should never be more than one, but this should self-correct if it
                            elem.is_latest = False  # does happen
                            elem.save()
