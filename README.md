# KAILASA's Social Media Restreaming Cloud Server Setup

This document will guide you on setting up a cloud streaming server (running Ubuntu Server) to monitor a youtube channel for livestreams and restream any livestream to a set of pre-configured destinations on social media.

Table of contents
=================
<!--ts-->
   * [How it works](#how-it-works)
   * [Components in the Project](#components-in-the-project)
   * [Setup Instructions](#setup-instructions)
   * [FAQs](#faqs)
<!--te-->




How it works
============

Essentially the workflow of our complete application is as follows:

1. User registers for a free account on Restream.io (https://restream.io)
2. User connects his/her Youtube, Twitter and Twitch accounts to their newly registered Restream.io account
3. User visits OUR platform and connects his/her restream.io account to our platform
4. Our platform monitors a youtube channel (SPH Nithyananda) for any live events and on detecting a live video, pulls that video stream and re-streams it to all the connected Restream.io accounts. The Restream.io platform in turn re-streams the stream it receives to that each user's connected Youtube/Twitter/Twitch accounts.
5. The stream pathway can be summarised as follows:
    * Youtube Channel (SPH Nithyananda) -> Our Cloud Server (Single) => Restream.io accounts (Multiple) => Youtube/Twitter/Twitch Accounts (Multiple)




Components in the Project
=========================

The entire livestreaming mechanism has has the following components:

#### 1. Restream.io (3rd party public platform)
We are using the Restream.io platform as an intermediary to stream to the social media platform destinations. Restream.io provides very useful features which allow us to connect mutiple of our social media accounts to it. We receive a single stream key to which we have to stream, and the Restream.io platform in turn 're-streams' it to all the platforms that we have connected. The important feature is that Restream.io is able to create and publish live events on Youtube and Twitter end-to-end without any manual intervention i.e. without us having to manually open the live stream dashboard on Youtube/Twitter and publish the incoming livestream. This is the reason we are using this platform. 


#### 2. Frontend Interface
This is a basic frontend webpage developed using Vue JS and Quasar frameworks. It is essentially a web form which allows 3rd party users to connect their restream.io accounts to OUR restreaming platform. The form has fields such as account title, and public URL so that we can collect information about which platforms are connected as destinations for restreaming. Quasar components take care of the browser-side validation of the form fields to ensure URLs entered are semantically correct, etc.

Upon submission of the form by the user, the webpage redirects to the backend server and passes the submitted form information to it. The backend server redirects the user to the restream.io account login screen, and asks them to grant access to our custom Restream.io Developer application. This would allow our application to have access to the user's Restream.io account, and allow us to send a stream to their restream.io account.


#### 3. Node JS Backend Server
This is a basic web server running on Node JS and using Express JS framework. Its job is to function as the backend server for the frontend interface which allows 3rd party users to connect their restream.io accounts to our application. This backend server listens for incoming requests from the frontend interface which contain information filled by users about their social media platforms.

Upon receiving a form submission request, the backend server stores the form data to the Mongo DB cloud database and redirects the user's browser to the Restream.io API connection webpage. This webpage prompts the user to login with their Restream.io account and allow access to our custom developer application on Restream.io. Upon successful user login and access granting, the backend server receives an access token and a refresh token along with information about the user's Restream.io account. These tokens allow the platform to perform actions on the user's behalf such as streaming to the user's connected platforms on Restream.io. The backend server stores both of these tokens as well as information about the Restream.io account on the Mongo DB cloud database.

At the end of a successful complete form submission from the user, the MongoDB database has a new entry added which contains user-submitted information, their Restream.io account information, and access keys to their Restream.io accounts.


#### 4. MongoDB Cloud Database
This is a No-SQL database hosted using MongoDB Cloud Atlas's (https://cloud.mongodb.com) free tier option. This database stores information about the social media platform destinations that we want to restream to. Each entry in this database is generated after a user fills the form on the 2. Frontend interface. Each entry will contain the access token and refresh token of a particular user's restream.io account, along with the data they filled in the form which includes their youtube channel URL, twitter profile URL, and twitch URL. The application later on uses the information in this database, while starting the streaming process. When the application detects that a livestream has started on the main SPH Nithyananda channel, it scrapes the title from the livestream. Next, it parses through each connected restream.io account stored in this database, and updates the default title of the video with the currently scraped title. Next it fetches the stream key of that particular restream.io account, and adds its entry in the NimbleStreamer running on the Ubuntu livestreaming server. This sends the restream of the SPH Nithyananda channel's live video to that particular restream.io account, which in turn streams to all the connected social media platforms like youtube, twitter, twitch, etc.


#### 5. Cloud Server
This is a cloud VPS machine running Ubuntu 20.04 LTS. The current instance of the setup is hosted on a service provider called Servercheap (https://servercheap.net). However, the hosting can be changed to any decent VPS provider with the following specifications:
- **OS:** Ubuntu 20.04 
- **RAM:** at least 2GB
- **CPU:** at least 2 vCPUs
- **Network:** Unlimited/Unmetered incoming and outgoing data bandwidth **(important - NO DATA LIMIT)** 
- **Port Speed:** 1Gbps port speed - This is recommended for high number of destinations to restream to. The estimated requirements are calculated as follows:
    * 1 incoming stream at 1500Kbps bitrate (720p quality)
    * X number of outgoing streams at 1500Kbps bitrate (720p quality)
    * After empirical testing, each outgoing stream requires a bandwidth of 4Mbps, so a 1Gbps port connection can support 220+ outgoing destinations comfortably (900/4)
    * Note: Most VPS providers won't be able to guarantee 1Gbps port speed even if advertised. The advertised 1Gbps speed is mostly shared within their data center. For high reliability and ensured 1Gbps speed, a dedicated server with 1Gbps port speed needs to be purchased (Hetzner for $40/month is a good option for this). In case of cheaper alternatives, they may advertise 1Gbps but their actual performance is throttled which leads to many outgoing destinations not receiving the stream.

The currently implemented instance of the restreamer is hosted on Servercheap with the following configuration: SSD KVM VPS - 2GB Ram 60GB SSD 2CPU Cores @ $4.50/month. This specification advertises 1Gbps port speed, however is not guaranteed and usually maxes out at around 150Mbps.




Setup Instructions
==================

### Setup the Cloud Server

#### 1. Purchase a cloud VPS from any suitable hosting provider:
Login to the console with root or with a user with root permissions. 

#### 2. Secure the VPS Server:
Perform the following actions. Follow the steps in each URL given:
  * Change SSH access port from default 22 to some arbitrary port: https://docs.ovh.com/us/en/vps/tips-for-securing-a-vps/#changing-the-default-ssh-listening-port
  * Create and use a non-root user: https://maximorlov.com/4-essential-steps-to-securing-a-vps/#1-use-a-non-root-user
  * Update the system OS: https://docs.ovh.com/us/en/vps/tips-for-securing-a-vps/#updating-your-system
  * Setup SSH for the new user: https://maximorlov.com/4-essential-steps-to-securing-a-vps/#setup-ssh-for-the-new-user
  * Disable SSH Protocol 1:
    - Runt this command in terminal: ```nano /etc/ssh/sshd_config```
    - Find the following statement: ```# Protocol 2,1```
    - Replace it with: ```Protocol 2```
    - Restart the SSH service after making changes and save the file: ```Service ssh restart```

#### 3. Install NimbleStreamer:

Full guide here: https://wmspanel.com/nimble/install#os_ubuntu

Add following rep into /etc/apt/sources.list. Open it using:
```
sudo nano /etc/apt/sources.list
```
After the last line of the document, add the following line:
```
deb [trusted=yes] http://nimblestreamer.com/ubuntu bionic/
```
Save and exit the file

Run the following commands: 
```
wget -q -O - http://nimblestreamer.com/gpg.key | sudo apt-key add - 
sudo apt-get update --allow-unauthenticated
sudo apt-get install nimble
```

Using SFTP, replace the rules.conf and nimble.conf files inside the directory ```/etc/nimble/``` - replace these 2 files with the 2 corresponding files found in this Github repo in the nimblestreamer-config folder.

#### 4. Install Python

Check and make sure the latest version of Python is installed on the system. Follow the steps here: https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server

#### 5. Install required Python packages

In the terminal, enter the following command:

```
python3 -m pip install pytz asyncio aiohttp pymongo secure-smtplib youtube_dl dnspython
```

#### 6. Install youtube-dl

In the terminal, enter the following command:

```
sudo apt-get install youtube-dl
```

#### 7. Copy over the project source files to a directory in the home folder

E.g. If your username is 'social', then place the live_service.py file in the following directory:
```
/home/social/code/live_service.py 

```
Before copying the .py file, edit it using a text editor of your choice and replace the placeholder values at the top of the document, namely:
1. channel_url : URl of the youtube channel to monitor for live events
2. CLOUD_SERVER_IP : public IP of the Ubuntu server
3. NIMBLE_STREAMER_APPLICATION: Nimblestreamer application name - this is pre-configured in the rules.conf file from this repo. Update this value in the .py file if changed
4. NIMBLE_STREAMER_STREAM : Nimble streamer stream key - this is pre-configured in the rules.conf file from this repo. Update this value in the .py file if changed
5. NIMBLE_STREAMER_LOGIN : Nimble streamer application login ID - this is pre-configured in the rules.conf file from this repo. Update this value in the .py file if changed
6. NIMBLE_STREAMER_PWD : Nimble streamer application password - this is pre-configured in the rules.conf file from this repo. Update this value in the .py file if changed
7. RESTREAMIO_CLIENT_ID : Restream.io developer account client ID
8. RESTREAMIO_CLIENT_SECRET : Restream.io developer account client secret
9. MONGO_URI : MongoDB connection URI
10. LIVESTREAM_DESCRIPTION : Fixed description for all restreamed posts
11. Log file path: Create an empty file called monitor.log in the same directory as the live_service.py. Update the path of this file on line 53 of the .py file.

#### 8. Setup the python script as a system service:

This step will ensure that the Python script will always be running, and even if it crashes due to some error, it will start back up again as a system service. The python script needs to be running 24x7 so that it can monitor the youtube channel for any live events and trigger the restreaming process. Follow the steps below to setup the service:

Almost all versions of Linux come with systemd out of the box, but if your’s didn’t come with it then you can simply run the following command:

```
sudo apt-get install -y systemd
```

To check which version of systemd you have simply run the command:
```
systemd --version
```

Now, create a service file for the systemd as following. The file must have .service extension under /lib/systemd/system/ directory

```
sudo nano /lib/systemd/system/dummy.service
```

and add the following content in it (Update your python file path if different):

```
[Unit]
Description=Python livestreaming service
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 /home/social/code/live_service.py

[Install]
WantedBy=multi-user.target
```

Your system service has been added to your service. Let’s reload the systemctl daemon to read new file. You need to reload this deamon each time after making any changes in in .service file.

```
sudo systemctl daemon-reload
```

Now enable the service to start on system boot, also start the service using the following commands.

```
sudo systemctl enable dummy.service
sudo systemctl start dummy.service
```

Finally check the status of your service as following command.
```
sudo systemctl status dummy.service
```

In case the script is not running after crashing at some point, Use below commands to stop, start and restart your service manually:
```
sudo systemctl stop dummy.service          #To stop running service 
sudo systemctl start dummy.service         #To start running service 
sudo systemctl restart dummy.service       #To restart running service 
```

FAQs
====

### What other source files are required for the complete workflow?
There are 3 other modules which complete the workflow:
1. **MongoDB Database:** You can create a free account on MongoDB cloud atlas and replace the connection URI in the live_service.py in the appropriate location. Read the comments in the .py file to understand where the connection URI needs to be placed. This connection URI is sensitive and allows the application to connect to the DB to store and retrieve the connected restream.io accounts.
2. **Backend Node JS server:** This is stored in a separate Github repo (https://github.com/nithyanandauniversity/kailasasocialstream-nodeserver). This can be hosted on a free heroku account. Guide here: (https://scotch.io/tutorials/how-to-deploy-a-node-js-app-to-heroku). Once hosted, the heroku app will have a unique URL which needs to be updated in the front-end form as the destination of the form response after the user clicks on submit. Add this URL to the source files of the front end webpage and then build the project again. Deploy this new build to a website.
3. **Frontend form webpage:** This is also stored in a separate Github repo (https://github.com/nithyanandauniversity/kailasasocialstream/tree/restream-connect). The source files can be used to build the deployable files. The build files can be hosted on any free raw HTML hosting service like Githubb pages. Guide here: https://dannguyen.github.io/github-for-portfolios/lessons/deploy-github-pages/



### What to do if the livestream is not showing up on the connected social media platforms?
You can troubleshoot this issue by checking for the following:
1. Login to the restream.io dashboard of any one account connected and stored in the MongoDB database. Check if the livestream is being received. If yes, then the issue is not with our streaming system. This can usually be fixed by disconnecting and reconnecting the social media account in the restream.io account. E.g. disconnect your youtube channel from your restream.io account and reconnect it by going through the login and authorization process again. Do the same for twitch/periscope-twitter. This disconnection/reconnection should be done by any person who is not seeing the livestream on their social media channels.
2. If the issue still persists, ensure that the python system service is running by checking its status. If not running, restart it.
3. If the issue still persists, restart the python system service - in case it has crashed unusually.
4. If the issue still persists, check the monitor.log file for the console output of the running python service. This will show at what step of the process an error is occurring (if any)



### What to do if the livestream published on the social media platforms is choppy/breaking/ending soon after starting/starting on some platforms but not on others?

In this case, it is probably the case that the streaming server is maxing out its hardware - specifically the network port speed. The amount of data being streamed out per second is higher than the hardware supports (if your server has a 150Mbps port speed), or the cloud provider is throttling the port speed and is not providing a 1Gbps connection. Some providers advertise 1Gbps but it is actually shared between all of their users, so in that case they throttle the port speed. To remedy this, the cloud provider will need to be changed to a service which will guarantee 1Gbps port speed / OR the quality of restream can be reduced to 480p to reduce the per second outgoing data - this will not work beyond a certain poing if the no. of destinations increase to a large number.

To verify this, you can SSH into the server and run the ```top``` command to monitor the system resources usage. Check whether the CPU %, or the RAM is maxing out. If so, upgrade your server specifications.

In case the CPU and RAM are not maxed out, check the network usage using the ```nload``` command (Install guide here: https://www.geeksforgeeks.org/how-to-install-nload-in-linux/). Type in ```sudo nload``` and monitor the graphs and values on all 4 of the interfaces (eth0/1/2/3 - toggle viewing these using the up-down arrow keys when seeing the graphs). Find the interface which has the most incoming/outgoing (this corresponds to the FFMPEG docker instance). Check if the max outgoing data per second is being throttled by the port speed of the server. The avg outgoing bitrate of 1 restream has been set to a default of 1500kbps for 720p in the .py file. Multiply the no. of restream destinations by this value and check if it exceeds the avg. outgoing data rate shown in nload. If yes, this means that the server provider is throttling the port speed.
