import lazycred

lazycred.set_config({
    "s3_path": "eFart/credentials/",
    "key_alias": "eFart-key",
    "region": "us-east-1"
    })

key = 'something'
val = 'Something Something Danger Zone'

lazycred.put(key, val)
print((lazycred.get(key)))
