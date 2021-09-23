import os
from unittest.mock import patch, mock_open
from pathlib import Path

import tarfile

from django.utils import timezone

import code_manager.tasks
from game_engine.models import User, UserCode
from code_manager.tasks import check_identity

from django.test import TestCase
from django.core.cache import cache

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


# Create your tests here.
class CodeManagerTest(TestCase):
    def setUp(self) -> None:
        pass

    def test_check_identity_invalid_1(self):
        with patch('builtins.open', mock_open(read_data='totallynotvaliddata')):
            res = check_identity("foo")  # not actually opening anything
            self.assertEqual(None, res)

    def test_check_identity_invalid_bad_email_2(self):
        with patch('builtins.open', mock_open(read_data='Email address: www.google.com')):
            res = check_identity("foo")
            self.assertEqual(None, res)

    def test_check_identity_invalid_only_email_3(self):
        with patch('builtins.open', mock_open(read_data='Email address: someone@example.com')):
            res = check_identity("foo")
            self.assertEqual(None, res)

    def test_check_identity_invalid_only_stu_num_4(self):
        with patch('builtins.open', mock_open(read_data='Student number: 18012345')):
            res = check_identity("foo")
            self.assertEqual(None, res)

    def test_check_identity_invalid_bad_stu_num_5(self):
        with patch('builtins.open', mock_open(read_data='Student number: abcdefg')):
            res = check_identity("foo")
            self.assertEqual(None, res)

    def test_check_identity_valid_1(self):
        with patch('builtins.open',
                   mock_open(read_data='Email address: someone@example.com\nStudent number: 18012345')):
            res = check_identity("foo")
            self.assertEqual((18012345, 'someone@example.com'), res)

    def test_create_user(self):
        user_details = {"student_id": 12345678,
                        "email_address": "email@example.com",
                        "github_username": "GitHubUsername"}
        code_manager.tasks.create_user(**user_details)
        self.assertEqual(User.objects.filter(**user_details).count(), 1)


class TemplateCloningTest(TestCase):
    def setUp(self) -> None:
        self.test_cache_key = 'test-cache-key'
        self.test_update_key = 'test-update-key'

    @staticmethod
    def get_files_in_directory(path):
        test_out_files = set()
        for parent_path, _, filenames in os.walk(path):
            parent_path = Path(parent_path)
            for name in filenames:
                np = parent_path.joinpath(name)
                test_out_files.add(str(np.relative_to(path)))
        return test_out_files

    @staticmethod
    def mock_clone_repo(_, output_dir):
        output_dir_path = Path(output_dir)
        with open(os.path.join(__location__, "sample_template.tar"), "rb") as in_tar:
            with tarfile.open(fileobj=in_tar) as tf:
                tf.extractall(output_dir)
        with open(output_dir_path.joinpath(Path('test_file_sentry')), 'wb') as outfile:
            outfile.write(b"Yep.")

    def set_template_cache(self):
        with open(os.path.join(__location__, "sample_template.tar"), "rb") as in_tar:
            cache.set(self.test_cache_key, in_tar.read())

    @staticmethod
    def get_template_files():
        with open(os.path.join(__location__, "sample_template.tar"), "rb") as in_tar:
            with tarfile.open(fileobj=in_tar) as tf:
                actual_files = {a.name for a in tf.getmembers() if a.isfile()}
        return actual_files

    def test_tarfile_extract(self):
        with open(os.path.join(__location__, "sample_template.tar"), "rb") as in_tar:
            with tarfile.open(fileobj=in_tar) as tf:
                actual_files = {a.name for a in tf.getmembers() if a.isfile()}

        with open(os.path.join(__location__, "sample_template.tar"), "rb") as in_tar:
            temp_dir = code_manager.tasks.extract_from_bytes_to_temp(in_tar.read())

        test_out_files = self.get_files_in_directory(temp_dir.name)
        self.assertSetEqual(test_out_files, actual_files)

    def test_update_template(self):
        sentry_filename = 'test_file_sentry'
        with patch('code_manager.tasks.clone_repo', wraps=self.mock_clone_repo):
            temp_dir, repo_instance = code_manager.tasks.update_template(self.test_cache_key, self.test_update_key)
            self.assertTrue(Path(temp_dir.name).joinpath(sentry_filename).exists())

        template_repository = cache.get('test-cache-key')
        temp_dir = code_manager.tasks.extract_from_bytes_to_temp(template_repository)

        test_out_files = set()
        for _, _, filenames in os.walk(temp_dir.name):
            for filename in filenames:
                test_out_files.add(filename)

        self.assertIn(sentry_filename, test_out_files)

    def test_get_template_no_explicit_expired(self):
        self.set_template_cache()
        actual_files = self.get_template_files()

        with patch('code_manager.tasks.update_template',
                   wraps=code_manager.tasks.update_template) as update_template_mock:
            td, repo = code_manager.tasks.get_template(cache_key=self.test_cache_key,
                                                       update_time_key=self.test_update_key)
            files_from_template = self.get_files_in_directory(td.name)

            self.assertEqual(files_from_template, actual_files)
            update_template_mock.assert_called_once()

    def test_get_template_no_explicit_not_expired(self):
        self.set_template_cache()
        actual_files = self.get_template_files()

        cache.set(self.test_update_key, timezone.now())

        with patch('code_manager.tasks.update_template',
                   wraps=code_manager.tasks.update_template) as update_template_mock:
            td, repo = code_manager.tasks.get_template(cache_key=self.test_cache_key,
                                                       update_time_key=self.test_update_key)
            files_from_template = self.get_files_in_directory(td.name)

            self.assertEqual(files_from_template, actual_files)
            update_template_mock.assert_not_called()

    def test_get_template_explicit_update(self):
        self.set_template_cache()
        actual_files = self.get_template_files()

        cache.set(self.test_update_key, timezone.now())

        with patch('code_manager.tasks.update_template',
                   wraps=code_manager.tasks.update_template) as update_template_mock:
            td, repo = code_manager.tasks.get_template(cache_key=self.test_cache_key,
                                                       update_time_key=self.test_update_key,
                                                       update=True)
            files_from_template = self.get_files_in_directory(td.name)

            self.assertEqual(files_from_template, actual_files)
            update_template_mock.assert_called_once()

    # this kinda also tests `create_or_update_user_code`...
    def clone_from_template_test(self):
        self.set_template_cache()
        cache.set(self.test_update_key, timezone.now())

        user = User.objects.create(student_id=12345678)

        self.assertIsNone(UserCode.objects.filter(user=user).first())
        code_manager.tasks.clone_from_template(user, cache_key=self.test_cache_key,
                                               update_time_key=self.test_update_key, )
        self.assertIsNotNone(UserCode.objects.filter(user=user).first())
