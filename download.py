## DIR-505 SharePort file download ##
##
## Written using a D-link DIR-505 running firmware version 1.09.
##
## This version seems to have a bug where read-only users can't list files in 
## the 'folder view' mode. Because of this, the user specified needs to have
## read and write access.
##
## Note that this download is not recursive.
##
## When authenticating (using a web browser), the DIR-505 shareport system will
## direct the user to make a GET request to the login URL with no parameters. 
## This returns a JSON response with several parameters. The two parameters to 
## look out for in this response are 'uid' and 'challenge'. The former will 
## serve as an access key once authenticated, and the latter will be used to 
## hash the password from the login form. The 'uid' value should be saved to a 
## cookie for future use.
##
## Once this JSON reply has been received, the 'challenge' parameter is added 
## to the end of the username and hashed with HMAC-MD5, with the key for this 
## hash being the plaintext password. This operation occurs in javascript on 
## the client side. The hashed value forms the 'password' value for the final
## login request.
##
## Now that the challenge has been completed, the username and hashed value 
## are posted to the login URL. If successful, the cookie created earlier can 
## now serve as an authentication token for future requests.
##
## You can now make direct requests to the file API to discover files and 
## directories on the connected USB stick. The same token can be used to 
## download files from the USB stick.
##
## toxicantidote.net - September 2017
##

## Dlink DIR-505 host/IP, port (default 8181), username and password
dirHost = 'dir-505 host'
dirPort = 8181
dirUser = 'username'
dirPass = 'password '

## USB device path
usbPath = 'folder/on/usb/device'

## Save path
savePath = '/full/path/to/save/to'

### END OF SETTINGS ###
import requests
import hmac
import os
import re

loginAPI = 'http://' + dirHost + ':' + str(dirPort) + '/dws/api/Login'
fileAPI = 'http://' + dirHost + ':' + str(dirPort) + '/dws/api/ListFile'
downloadPath = 'http://' + dirHost + ':' + str(dirPort) + '/usb_dev/usb_A1/' + usbPath
token = None

## Get the login parameters
req = requests.get(loginAPI)

json = req.json()
if json['status'] == 'ok':
	userID = json['uid']
	challenge = json['challenge']
	token = dict(uid = userID)
	print('Got challenge ' + challenge)
	print('UID for cookie is ' + str(userID))
	
	## Work out the HMAC-MD5 digest for the password from the given challenge
	password = hmac.new(bytes(dirPass, 'utf-8'), bytes(dirUser + challenge, 'utf-8')).hexdigest()	
	print('HMAC-MD5 password is ' + password)
	
	## Perform the login
	post_payload = {'id': dirUser, 'password': password}
	req = requests.post(loginAPI, data = post_payload, cookies = token)
	
	## Check that the login succeeded
	json = req.json()
	if json['status'] != 'ok':
		print('Login failed')
		token = None
	else:
		print('Login successful')
		
if token != None:
	## Get the list of files
	req = requests.get(fileAPI + '?id=dirUser&tok=&volid=1&path=path=usb_dev/usb_A1/' + usbPath, cookies = token)
	json = req.json()
	
	## If there are none, do nothing
	if json['count'] == 0:
		print('No files for transfer')
	else:
		## Download each of the files one by one
		fileList = json['files']
		os.chdir(savePath)
		for fileEntry in fileList:
			## Make sure there are no path components in the response (very 
			## basic MiTM protection, but by no means foolproof)
			name = re.sub(r'[\\\/]', '', fileEntry['name'])
			size = fileEntry['size']
			
			print('Downloading file ' + name + ' (size ' + str(size) + ' bytes)...')
			
			## Get the file. Remember to pass UID cookie to allow access
			req = requests.get(downloadPath + '/' + name, cookies = token)
			## Make sure we got HTTP code 200/OK (the actual file)
			if req.status_code == '200':
				saveSock = open(name, 'wb')
				saveSock.write(req.content)
				saveSock.flush()
				saveSock.close()
				## Check that the saved size matches the size reported by the 
				## device, otherwise it might be an incomplete download.
				saveSize = os.path.getsize(name)
				if size != saveSize:
					print('Expected ' + str(size) + ' bytes, but got ' + str(saveSize) + ' bytes!')
			else:
				print('Received HTTP error ' + str(req.status_code) + ': ' + str(req.text))
				
## All done!
print('All done!')
