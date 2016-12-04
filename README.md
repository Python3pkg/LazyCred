# LazyCred
Minimalistic implementation of credential/secret storage using AWS S3 and KMS.

## Installation

```bash
pip install git+git://github.com/2deviant/LazyCred.git
```

## Use
### Command Line

**Set a value from a file**:

```bash
~> lazycred put db_credentials db_creds.json
```

**From standard input**:

```bash
~> lazycred put db_credentials < db_creds.json
```
or

```bash
~> cat db_creds.json | lazycred put db_credentials
```

**Get the value**:

```bash
~> lazycred get db_credentials
```

### Python
```python
import lazycred

key = 'something'
val = 'Something Something Danger Zone'

lazycred.put(key, val)
print(lazycred.get(key))
```

#### Note
Secrets stored from [inside Python](sample.py) are accessible to the command line, and *vice versa*, of coruse.

## Configuration
In descending order of priority:
### Inline
Only available inside Python:

```python
import lazycred

lazycred.set_config({
    "s3_path": "eFart/credentials/",
    "key_alias": "eFart-key",
    "region": "us-east-1"
    })
```

* `s3_path` refers to the S3 bucket `eFart` and folder `credentials/`.  Folder is not require however, `s3_path` must at least contain the bucket followed by `/`.
* `key_alias` is the alias of the KMS key.
* `region` is self-explanatory.


### File
**`.lazycred`**:

```json
{
    "region": "us-east-1",
    "s3_path": "eFart/credentials/",
    "key_alias": "eFart-key",
}
```

This file is sought in the following manner:

1. Check the current folder;
2. If doesn't exist, go up a folder and try again;
3. Continue until the root folder, `/`, is reached;
4. If not found, attempt to source from `$HOME`.

### Environment Variables
LazyCred will attempt to source the values from environment variables if `.lazycred` is not found:

* `LAZYCRED_S3_PATH`
* `LAZYCRED_KEY_ALIAS`
* `AWS_DEFAULT_REGION`

## Requirements
1. AWS Account
1. AWS S3 bucket in the nether region (regionless)
2. AWS KMS key

## Potential Issues
### Speed
![](slow.jpg)

LazyCrypt relies on two remote, distinct services: S3 and KMS.  S3 is optimized for bulk storage and fast downloads, not rock-bottom latency.  Add to that the transit time for your request and payload return, add to that the same for KMS.  What results is a function that is best not called from a tight loop.  Recommended use is at the start of an application.

#### Blob Storage
To counteract low retrieval speed, one may store all of the secrets as one JSON blob.

## Shop
### Dependencies
Outside of Python's pre-packaged libraries:

* Boto
* cryptography

To install:

```bash
pip install boto cryptography
```

### Boto
Boto v2 is implemented.  AWS credentials are sourced from their default locations.  For more information, see [Boto Documentaiton](http://boto.cloudhackers.com/en/latest/boto_config_tut.html).

### Error Handling
In case of any error, be it configuration, communication, or cryptography, **get** returns `None`, and **put** returns `False`.  In such case, error is logged with all available details via Python's `logging` module:

```bash
> lazycred get SpaceBalls
ERROR:LazyCredLogger:Unable to get <Key: eFart,credentials/SpaceBalls>.
```
If your application has a log collector, it will sweep up LazyCred's errors.

### Storage
Data is stored at an S3 path specified in the configuration suffixed with the key name.  A typical record looks like so:

```json
{
    "data": "gAAAAABYOhZbt6reGldBveQ...",
    "key": "jodC9cIM/FT7skOoWZrm0QAA..."
}
```
Where `data` is the payload and `key` is the KMS-encrypted random Fernet key.  AWS KMS decrypts the `key`, then the decrypted key decrypts the `data`.  One may note that `key_alias` is not specified, that is because the reference to the KMS key is encoded in the `key` cipherblob.

### Intermediary Key
One may wonder why not encrypt the data directly with KMS.  AWS KMS is limited to a 4KB payload.  While most credential store items are less than 4KB, that limit is by no means guaranteed.  A common practice is to encrypt an arbitrary amount of data with a random, fixed-size key, and then encrypt the key with KMS (same protocol as PGP).  Both methods produce cryptographically equivalent results provided that both use equivalent encryption methods.

### Code Penmanship
An astute coder notices that this small application encompasses the following four concepts:

* Key, as it pertains to key-value store nature of LazyCred;
* Key, _a.k.a._ everything after the bucket name in an S3 path;
* Key, a sequence of random characters used to encrypt data;
* Key, KMS key -- and an alias thereto -- used to encrypt the key from above.

A moderate effort has been made to contain the ambiguity however, some variable alliteration cannot be helped.