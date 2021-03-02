# Edit this file with your details inside the parenthesis.

### General Script Parameters ###

# Politics and War API Key
key = ""

# Politics and War Login Credentials. This user will be the one sending the messages.
email = ""
password = ""

# your alliance ID
alliance_id = ""

# This setting determines if the script will loop and keep messaging after a successful execution. Set True to run
# continuously, and False to run once and then exit. If False, you will need to manually run the script every time you
# want to send messages.
run_continuous = True

# Enter the time to wait in seconds between each pass of the script when running in continuous mode. Default is 180,
# which will cause the script to pause for 3 minutes after completion before running itself again. Lower numbers have a
# higher chance of messaging a nation immediately after they are created or leave their alliance, but will use up your
# daily API quota much faster. I do not recommend going below 60 seconds.
pause_time = 180

### Messaging Paramters ###

# In message body or subject, [[ruler]] and [[nation]] can be used as stand-ins for the recipients ruler and nation
# name. The script will automatically swap it out for their details before sending the message, giving it a personalized
# touch.

# Subjects cannot exceed 50 characters, or the game will not send the message.

### Recruitment Messagenger  ###
recruiter_subject = ""
recruiter_body = """ """
# set True if you want to exclude inactive nations from being messaged, and False to message everyone.
exclude_inactive = False
# Define inactivity. This setting can be ignored if you left exclude_inactive as false. If it is True, set below the
# maximum number of minutes a recipient can be inactive. Any nation over that amount will not be messaged. Default is
# 4320 minutes (3 days).
inactivity_threshold = 4320

### Applicant Messenger Parameters ###

# This setting enables/disables the applicant messenger. Set True to active, and False to leave off.
applicant_messenger_active = False
applicant_subject = ""
applicant_body = """ """


### Script Stuff, Don't Edit ###
recruitment_message = {'subject': recruiter_subject, 'body': recruiter_body}
applicant_message = {'subject': applicant_subject, 'body': applicant_body}
login_payload = {
    'email': email,
    'password': password,
    'loginform': 'login'
}
