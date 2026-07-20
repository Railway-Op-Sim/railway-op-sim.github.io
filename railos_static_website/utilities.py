import hashlib


def hash_file(file_path: str) -> str:
    BUF_SIZE = 65536

    sha1 = hashlib.sha1()

    with open(file_path, 'rb') as f:
        while True:
            if data := f.read(BUF_SIZE):
                sha1.update(data)
            else:
                break
    return sha1.hexdigest()
