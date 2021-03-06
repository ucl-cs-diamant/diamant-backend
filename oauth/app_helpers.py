import os
import textwrap
from binascii import hexlify


def generate_user_token():
    key = hexlify(os.urandom(30)).decode()
    dashes_key = '-'.join(textwrap.wrap(key, 15))

    return dashes_key


def generate_random_verification_code():
    key = hexlify(os.urandom(40)).decode()
    final = "verify" + key
    return final
