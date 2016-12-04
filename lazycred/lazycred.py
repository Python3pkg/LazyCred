"""
LazyCred
"""

import base64
import boto.kms
from cryptography.fernet import Fernet
import json
import logging
import os

LAZYCRED_LOG_NAME = 'LazyCredLogger'
LOCAL_CONFIG_FILE = '.lazycred'
ENV_PATH_VARIABLE = 'LAZYCRED_S3_PATH'
ENV_KMS_KEY_ALIAS = 'LAZYCRED_KEY_ALIAS'
ENV_REGION_STRING = 'AWS_DEFAULT_REGION'
ROOT_FOLDER_SLASH = '/'

# custom logger
logging.basicConfig()
logger = logging.getLogger(LAZYCRED_LOG_NAME)

# inline configuration
aws_config = None

def _memorize(function):
    """
    Not importing a whole module for this.
    """
    class Memorizer(dict):
        """
        Self-populating dictionary.
        """
        def __init__(self, function):
            super(Memorizer, self).__init__()
            self.function = function
        def __call__(self, *args):
            key = str(args)
            if key not in self:
                self[key] = self.function(*args)
            return self[key]
    return Memorizer(function)

@_memorize
def _get_aws_config():
    """
    Find the AWS configuration and return it.
    """

    def __get_file_contents(file_name):
        """
        Self-explanatory.
        """
        try:
            with open(file_name, 'r') as config:
                return __verify_mandatatory_fields(json.loads(config.read()))
        except IOError as e:
            logger.error(
                'Unable to read from configuration file ::: {}'.format(e)
                )
        except ValueError as e:
            logger.error('Invalid configuration ::: {}'.format(e))
        return None

    def __verify_mandatatory_fields(config):
        """
        Make sure we have all of the fields.
        """
        mandatory_fields = ['s3_path', 'region', 'key_alias']
        all_present = not False in [_ in config for _ in mandatory_fields]
        if all_present:
            return config
        else:
            logger.error(
                'Configuration is missing a mandatory field ::: {!r}'.format(
                    mandatory_fields
                    )
                )
        return None

    # inline configuration overrides system defaults
    if aws_config:
        return __verify_mandatatory_fields(aws_config)

    # [try to] read the configuration from a file
    folder_prefix = ''
    logger.debug(
        'Attempting to source configuration from {!r}'.format(LOCAL_CONFIG_FILE)
        )
    # go up a folder until the file is found or the root folder is reached
    while not os.path.isfile(folder_prefix + LOCAL_CONFIG_FILE):
        if os.path.realpath(folder_prefix) == ROOT_FOLDER_SLASH:
            break
        folder_prefix = '../' + folder_prefix
    # file found, try to read it
    else:
        return __get_file_contents(folder_prefix + LOCAL_CONFIG_FILE)

    # look in the user folder
    user_lazycred = '{}/{}'.format(os.path.expanduser('~'), LOCAL_CONFIG_FILE)
    if os.path.isfile(user_lazycred):
        return __get_file_contents(user_lazycred)

    # if the file is not found, try to get the configuration from the
    # environment variables
    logger.debug(
        'Configuration file not found.  Attempting to source configuration '
        'from environment variables.'
        )

    required_variables = {
        'region': ENV_REGION_STRING,
        's3_path': ENV_PATH_VARIABLE,
        'key_alias': ENV_KMS_KEY_ALIAS
        }

    configuration = {
        key: os.environ.get(required_variables[key], None)
        for key in required_variables
        }

    if None in configuration.viewvalues():
        logger.error(
            'Unable to find configuration in environment variable(s).'
            )
    else:
        return configuration
    return None

def _get_s3_object(file_name):
    """
    Instantiate and return an AWS S3 object.
    """
    aws_configuration = _get_aws_config()
    if aws_configuration:
        try:
            # separte the bucket name form the path of the repository
            bucket_name, prefix = aws_configuration['s3_path'].split('/', 1)
            # connect to the bucket
            bucket = boto.connect_s3().get_bucket(bucket_name)
            # instantiate a key object
            s3_object = boto.s3.key.Key(bucket)
            s3_object.key = prefix + file_name
        except Exception as e:
            logger.error('Unable to connect to AWS S3 ::: {}'.format(e))
        else:
            return s3_object
    return None

def _get_kms_crypto():
    """
    Connect to AWS KMS and return a(n) (de|en)cryptor.
    """
    aws_configuration = _get_aws_config()
    if aws_configuration:
        crypto = boto.kms.connect_to_region(aws_configuration['region'])
        if crypto:
            return crypto
        logger.error(
            'Unable to connect to AWS KMS in {!r}.'.format(
                aws_configuration['region']
                )
            )
    return None

def _kms_encrypt(plaintext):
    """
    Encrypt some data using AWS KMS and return a B64 crypt.
    """
    encryptor = _get_kms_crypto()
    if encryptor:
        try:
            ciphertext = encryptor.encrypt(
                'alias/' + _get_aws_config()['key_alias'], plaintext
                )
        except Exception as e:
            logger.error('Unable to encrypt with AWS KMS ::: {}'.format(e))
        else:
            return base64.b64encode(ciphertext['CiphertextBlob'])
    return None

def _kms_decrypt(ciphertext):
    """
    Decrypt a B64 crypt (result of _kms_encrypt()) using AWS KMS.
    """
    decryptor = _get_kms_crypto()
    if decryptor:
        try:
            plaintext = decryptor.decrypt(base64.b64decode(ciphertext))
        except Exception as e:
            logger.error('Unable to decrypt with AWS KMS ::: {}'.format(e))
        else:
            return plaintext['Plaintext']
    return None

def _encrypt(data):
    """
    Encrypt data and return a dictionary containing the
    encrypted key and the data encrypted with said key.
    """
    try:
        # generate a random key
        cipher_key = Fernet.generate_key()
        # encrypt the data
        cipher_text = Fernet(cipher_key).encrypt(data)
    except Exception as e:
        logger.error('Unable to encrypt ::: {}'.format(e))
    else:
        # return the KMS-encryped key and the encrypted data
        return {
            'key': _kms_encrypt(cipher_key),
            'data': cipher_text
            }
    return None

def _decrypt(encrypted_data):
    """
    Decrypt the data blob.
    """
    try:
        encrypted_data = json.loads(encrypted_data)
        # instantiate the fernet decryptor with the key, which
        # used to be encrypted with AWS KMS, which was randomly
        # generated by _encrypt(), and stored along with the data
        # in its KMS-encrypted state
        fernet = Fernet(str(_kms_decrypt(encrypted_data['key'])))
        # decrypt the data
        data = fernet.decrypt(str(encrypted_data['data']))
    except ValueError as e:
        logger.error('Corrupt crypto S3 blob ::: {}'.format(e))
    except Exception as e:
        logger.error('Unable to decrypt S3 blob ::: {}'.format(e))
    else:
        return data
    return None

def get(key):
    """
    Read a value for a given key.
    """
    s3_object = _get_s3_object(key)
    if s3_object:
        # [try to] read from S3
        try:
            encrypted_data = s3_object.get_contents_as_string()
        except boto.exception.S3ResponseError as e:
            logger.error('Unable to get {!r} ::: {}'.format(s3_object, e))
        else:
            # decrypt and return if successful
            return _decrypt(encrypted_data)
    return None

def put(key, data):
    """
    Store key-value pair.
    """
    # "connect" to S3
    s3_object = _get_s3_object(key)
    if s3_object:
        # encrypt the data
        encrypted_data = _encrypt(data)
        # write data to S3
        try:
            s3_object.set_contents_from_string(json.dumps(encrypted_data))
        except Exception as e:
            logger.error('Unable to put {!r} into {!r}.'.format(key, s3_object))
        else:
            return True
    return False

