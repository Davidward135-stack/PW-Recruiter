from applicant_messenger import message_applicants
from unaligned_messenger import recruit
from parameters import key, applicant_messenger_active

def main():
    if applicant_messenger_active:
        message_applicants(key)
    recruit(key)

if __name__ == "__main__":
    main()
