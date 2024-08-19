# PlanUs_event_hosting

## Overview
PlanUs is an event hosting website designed to enhance the overall event experience.

## Directory Structure
app/: This directory contains all the backend code including the database logic, authentication, routers for APIs, and also some authorisation code.

static/: This directory has some default mounted images such as default profile picture in it.

templates/: There are the HTML and HTMX frontend code.

tests/: It is for software testing using pytest. Simply run the command 'pytest'.

## Getting Started
If you want to run this app on your local machine:
First you need to install docker, and postgreSQL with pgAdmin on your machine.
Second change all the environment settings in the docker-compose.yml file. Change the environment part and the image environment part to match with your local machine.
Third, run 'docker-compose up --build'.
Then go to localhost:8000
