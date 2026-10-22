import os

### General Script Parameters ###

key = os.environ["PNW_API_KEY"]
email = os.environ["PNW_EMAIL"]
password = os.environ["PNW_PASSWORD"]

# Portal Raiders / future NOVA
alliance_id = "15689"

# GitHub Actions runs the script once each time
run_continuous = False
pause_time = 180

### Recruitment Message ###

recruiter_subject = "Your Nation. Your Decisions. 💚"

recruiter_body = """
<p style="text-align:center;"><img src="https://i.postimg.cc/N02h8y9w/IMG-8522.png">\</p>

<p>⚠️ <b>BANKING NOTICE</b> Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. <b>DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME.</b> Deposits made without the correct code may not be credited to your personal bank balance.</p>

<p><a href="https://politicsandwar.com/alliance/join/id=15689">APPLY IN-GAME</a></p>

<p><a href="https://discord.gg/zCxaUKfXza">DISCORD\</a></p>
"""

# Only recruit reasonably active nations
exclude_inactive = True

# 3 days in minutes
inactivity_threshold = 4320

### Applicant Messenger ###

applicant_messenger_active = False
applicant_subject = ""
applicant_body = ""

### Script Stuff ###

recruitment_message = {
    "subject": recruiter_subject,
    "body": recruiter_body
}

applicant_message = {
    "subject": applicant_subject,
    "body": applicant_body
}

login_payload = {
    "email": email,
    "password": password,
    "loginform": "login"
}
