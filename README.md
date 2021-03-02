# PW-Recruiter
Recruitment bot for Politics and War. Requires python and the requests package. 

You must configure the settings in parameters.py before running the script. 

CLI usage: python recruiter.py
Windows users can optionally run the message.bat file instead of the command line.

# Recruitment Function 

PW-Recruiter sends your recruitment message to all non-aligned nations who have not already been messaged. Recipients have their nation_id added to the logs.db file to filter them out on subisquent runs of the program. By defualt the program will loop every 3 minutes. Leave it open and running in the background if you want to keep it going at all times. 

Users can optionally exclude nations who have exceeded a set inactivity threshold. By default this is left off and all non-aligned non-vm nations will be messaged. This will also lead to a large volume of messages on the first run as it goes through all inactive nations in the game. Subsiquent runs will be much smaller and faster. 

# Applicant Messenger

Users can optionally have the script send a seperate message to all applicants of their alliance. This can be useful if you have lots of applicants who joined in-game but did not follow the rest of your procedure, such as joining a Discord or forum. This feature is off by default and must be enabled in the parameters.py


# Message Personalization 

For both the applicant and recruitment message, the subject and body can be personalized. Use [[ruler]] and [[nation]] as standins for the recipients ruler name and nation name, respectively. The script will automatically swap them out with the recipients details before sending the message. 


# Installation 

1. Windows users will need to install Python. 
2. Install the requests package for python.
3. Move the logs.db file from the sqlite folder up to the main script folder. (It is kept seperate here to prevent your database from being overwritten when pulling updates).

That's it!



