# import typing
from datetime import timedelta

from celery import shared_task
# import concurrent.futures

from django.core.files import File
from django.core.cache import cache
from django.utils import timezone

from game_engine.models import User, UserCode, UserPerformance

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


def create_user(student_id, email_address, github_username):
    # get_or_create should be redundant, but it never hurts to be cautious?
    # student_object, created = User.objects.get_or_create(email_address=email_address,
    #                                                      student_id=student_id,
    #                                                      github_username=github_username)
    # if not created:
    #     student_object.student_id = student_id
    #     student_object.student_email = email_address
    #     student_object.github_username = github_username
    #     student_object.save()
    User.objects.get_or_create(email_address=email_address,
                               student_id=student_id,
                               github_username=github_username)


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
        if User.objects.filter(github_username=username).exists():
            continue
        # if user not exist, clone repo, scan for ID, and create User
        with tempfile.TemporaryDirectory() as temp_dir:
            clone_repo(repo["clone_url"], temp_dir)

            # todo: ####  ADD A TOKEN CHECK, USERS WILL BE PRE-GENERATED INSTEAD OF BEING CREATED HERE ####
            for path in os.listdir(temp_dir):
                path = os.path.join(temp_dir, path)
                if not os.path.isfile(path) and os.stat(path).st_size >= 1024:  # skip over large files
                    continue
                if (identity := check_identity(path)) is None:
                    continue

                student_id, student_email = identity
                create_user(student_id, student_email, username)
                # print(f"Created user: {student_id} - {username}")
                break  # breaks inner loop, resumes outer loop


def get_template(update=False, cache_key='template_repository',
                 update_time_threshold: int = 3600,
                 update_time_key: str = 'template_repo_last_updated'):
    """

    :param update: Force updating template cache
    :param update_time_threshold: Time to keep template in cache before updating
    :param update_time_key: Key to use for template cache last updated time
    :param cache_key: Key to use for template cache
    :return: (TemporaryDirectory instance, Repo instance). tempdir instance is needed to keep it in scope
    """
    template_last_updated = cache.get(update_time_key)
    template_repository = cache.get(cache_key)
    if template_last_updated is not None and template_repository is not None:
        temp_dir = tempfile.TemporaryDirectory()
        with tempfile.TemporaryFile("w+b") as temp_outfile:
            temp_outfile.write(template_repository)
            temp_outfile.flush()
            temp_outfile.seek(0)
            with tarfile.open(fileobj=temp_outfile, mode='r') as template_tar:
                template_tar.extractall(temp_dir.name)

        repo_instance = Repo(temp_dir.name)
        # print(repo_instance.active_branch.commit.committed_datetime)

        # could be more efficient, but this was written at 4 in the morning
        # print((timezone.now() - template_last_updated), timedelta(seconds=update_time_threshold))
        if (timezone.now() - template_last_updated) <= timedelta(seconds=update_time_threshold) and not update:
            return temp_dir, repo_instance
        update = True

    if update or template_repository is None or template_last_updated is None:
        print(f"updating template cache, last update: {template_last_updated}")
        template_repo_url = "https://github.com/ucl-cs-diamant/bot-template.git"
        temp_dir = tempfile.TemporaryDirectory()
        clone_repo(template_repo_url, temp_dir.name)
        repo_instance = Repo(temp_dir.name)

        print(repo_instance.refs)

        archive = archive_directory(temp_dir.name)
        mem_buf_archive = archive.read()
        cache.set(cache_key, mem_buf_archive, timeout=None)
        cache.set(update_time_key, timezone.now(), timeout=None)

        return temp_dir, repo_instance


def clone_from_template(user_instance: User):
    td, template_repo = get_template()
    create_or_update_user_code(branch=(template_repo.active_branch.name, template_repo.active_branch.name),
                               clone_working_dir=td.name,
                               repo=template_repo,
                               user_instance=user_instance)


# def create_or_update_user_code(branch_name, clone_working_dir, repo, repo_default_branch, user_instance):
def create_or_update_user_code(branch: tuple, clone_working_dir, repo, user_instance):
    branch_name, repo_default_branch = branch

    code_instance = UserCode.objects.filter(user=user_instance, branch=branch_name).first()
    if code_instance is None:
        code_instance = UserCode(user=user_instance, branch=branch_name)
        code_instance.to_clone, code_instance.primary = (repo_default_branch == branch_name,) * 2
    save_code_archive(clone_working_dir, code_instance, repo, branch_name)
    code_instance.save()
    UserPerformance.objects.get_or_create(code=code_instance, user=code_instance.user)


def create_or_update_branches(user_instance: User, repo: Repo, clone_working_dir):
    repo_default_branch = repo.active_branch.name
    repo_branches = {line.strip().split('origin/')[-1] for line in repo.git.branch('-r').splitlines()}

    for branch_name in repo_branches:
        # code_instance, created = UserCode.objects.get_or_create(user=user_instance, branch=repo_branch_name)
        create_or_update_user_code(branch=(branch_name, repo_default_branch), clone_working_dir=clone_working_dir,
                                   repo=repo, user_instance=user_instance)


def archive_directory(directory):
    temp_file = tempfile.TemporaryFile()
    with tarfile.open(fileobj=temp_file, mode="w") as tar_out:
        for dir_entry in os.listdir(directory):
            # arcname removes temp_dir prefix from tar
            tar_out.add(os.path.join(directory, dir_entry), arcname=dir_entry)
    temp_file.seek(0)
    return temp_file


def save_code_archive(clone_working_dir, code_instance, repo, branch_name):
    if code_instance.commit_sha == repo.refs[f"origin/{branch_name}"].commit.hexsha:
        print(f"{branch_name} not changed")
        return

    repo.git.checkout(branch_name)
    branch_head_sha = repo.branches[branch_name].commit.hexsha
    repo_name = repo.remotes.origin.url.split('.git')[0].split('/')[-1]
    branch_head_commit_time = repo.active_branch.commit.committed_datetime

    code_instance.commit_sha = branch_head_sha
    code_instance.commit_time = branch_head_commit_time
    code_instance.has_failed = False

    temp_file = archive_directory(clone_working_dir)
    code_instance_filename = f"{repo_name}-{branch_name}-{repo.head.reference.commit.hexsha}.tar"
    code_instance.source_code.save(code_instance_filename, File(temp_file))


@shared_task
def clone_repositories():
    # todo: move prefix to config/env file
    prefix = "test-sample-code-"
    repos = list_classroom_repos(os.environ.get("GITHUB_API_TOKEN"), "ucl-cs-diamant", prefix=prefix)
    for repo in repos:
        username = repo["name"][len(prefix):]
        if (user_instance := User.objects.filter(github_username=username).first()) is not None:
            # if user exists, clone repo and tar directory
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_instance = clone_repo(repo["clone_url"], temp_dir)
                create_or_update_branches(user_instance, repo_instance, temp_dir)
