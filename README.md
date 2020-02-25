#To start your application using Flask-AppBuilder

## Install dependencies:
Some steps may require additional dependencies, the following will be enough
to cover the major components and doesn't cover dependencies that might
typically already be installed (python for example).
### Clone the project
    git clone https://github.com/gberl001/coffee_monitor_site.git
### Database setup
You will need MySQL or MariaDB installed

Create the schema for the website

    CREATE SCHEMA `fab_coffee_scale` DEFAULT CHARACTER SET utf8mb4 ;
    
Create the schema for the data itself
        
    CREATE SCHEMA `coffee_scale` DEFAULT CHARACTER SET utf8mb4 ;

Execute the following commands to create a user for the site to access data

    CREATE USER 'adminuser'@'localhost' IDENTIFIED BY 'adminPa$$word1!';
    GRANT ALL PRIVILEGES ON *.* TO 'adminuser'@'localhost';
    FLUSH PRIVILEGES;
    
### Python dependencies
#### Install Flask Appbuilder
    pip3 install flask-appbuilder
#### Install Mysql Client for SQLAlchemy
    pip3 install mysqlclient
I couldn't get this to work on Windows because it needed me to install
all sorts of dependencies. I ended up just installing the wheel file
from https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient

    pip3 install <path to wheel>

## Create a site admin user

    flask fab create-admin
Go ahead with the defaults and just add whatever password you want for your
admin user on the website.

## Run the server

    $ flask run --port 8080

