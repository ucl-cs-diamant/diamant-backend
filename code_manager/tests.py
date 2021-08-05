from unittest.mock import patch, mock_open
from .tasks import check_identity

from django.test import TestCase


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
