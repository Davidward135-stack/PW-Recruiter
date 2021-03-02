from applicant_messenger import message_applicants
from unaligned_messenger import recruit
from time import sleep
from parameters import key, applicant_messenger_active, pause_time


def main():
    if applicant_messenger_active:
        message_applicants(key)
    recruit(key)
    sleep(pause_time)


if __name__ == '__main__':
    while True:
        main()
