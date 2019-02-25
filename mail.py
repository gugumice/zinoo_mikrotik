#!/usr/bin/env python
import smtplib, sys
class gmail(object):
	def __init__(self):
		self._username='hab.ziino@gmail.com',
		self._password='brontes1',
		self._replyto='hab.ziino@gmail.com',
		self._s = smtplib.SMTP('smtp.gmail.com', 587)

	def sendmail(self,
			sendto='gunarsf@gmail.com,gunarsf@sms.lmt.lv',
			subject='hab_LMT',content='Test Message'):
		sendto=sendto.split(",")
		self._s.starttls()
		self._s.ehlo()
		try:
			self._s.login(self._username[0],self._password[0])
		except:
			print(self._username[0],self._password[0])
			sys.exit(2)
		
		mailtext='From: '+self._replyto[0]+'\nTo: '+",".join(sendto)+'\n'
		mailtext=mailtext+'Subject:'+subject+'\n'+content

		self._s.sendmail(self._replyto[0], sendto,  mailtext)
		#print(self._replyto[0], sendto, mailtext)
		return(self._s.quit())

g=gmail()
print(g.sendmail(sendto="gunarsf@gmail.com",content="hello"))
