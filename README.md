# PW-Recruiter
Recruitment bot for Politics and War. Requires python and the requests package.

PW-Recruiter sends your recruitment message to all non-aligned nations who have not already been messaged. Recipients have their nation_id added to the logs.db file to filter them out on subisquent runs of the program. By defualt the program will loop every 5 minutes. Leave it open and running in the background if you want to keep it going at all times .

You must edit message_info.py with a text editor. Include your details in the appropriate places between the quotation marks (API key, user credentials, subject, body). Subject cannot be more than 50 characters or PW won't send the message. [[ruler]] and [[nation]] can be used as standins in the subject or body. The script will replace that with the recipients ruler name or nation name respectively. 

Windows Usage: run the message.bat file to launch the script. 

Linux command: python recruit.py 

