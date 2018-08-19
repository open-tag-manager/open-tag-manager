import bcrypt
from getpass import getpass


def main():
    salt = bcrypt.gensalt(rounds=12, prefix=b'2b')
    password = getpass('Password: ')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    print(hashed_password)


if __name__ == '__main__':
    main()
