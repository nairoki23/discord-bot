from func.gmail.auth import GmailAuth
from func.gmail.service import GmailService
from func.gmail.process import GmailProcess 

auth=GmailAuth()
service=GmailService(auth.get_creds)
process=GmailProcess(service.service)
#service.start_listening()

message_ID=input()
m=process.process_message(message_ID)
print(m["from"],m["subject"])