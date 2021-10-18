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

#### 3. Install Python

Check and make sure the latest version of Python is installed on the system. Follow the steps here: https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server

#### 4. Install required Python packages

In the terminal, enter the following command:

```
python3 -m pip install pytz asyncio aiohttp pymongo secure-smtplib youtube_dl dnspython
```

#### 5. Install youtube-dl

In the terminal, enter the following command:

```
sudo apt-get install youtube-dl
```

#### 6. Copy over the project source files to a directory in the home folder

E.g. If your username is 'social', then place the live_service.py file in the following directory:
```
/home/social/code/live_service.py 

```

#### 7. Start the process:

Start the program by running the live_monitor.py python file using the following command:

```
python3 /home/<username>/code/live_monitor.py
```
