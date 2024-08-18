# PlanUs_event_hosting

PlanUs is an event hosting website:

Under the app dir, there are all the backend code including the database logic, authentication, routers for APIs, and also some authorisation code.

Under the static file, there is some default mounted images such as default profile picture in it.

Under the templates dir, there are the HTML and HTMX frontend code.

Under the tests dir, it is for software testing using pytest. Simply run the command pytest.

If you want to run this app on your local machine:
First you need to install docker, and postgreSQL with pgAdmin on your machine.
Second change all the environment settings in the docker-compose.yml file. Change the environment part and the image environment part to match with your local machine.

