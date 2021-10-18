# Textinator

## Installation
### Prerequisites
```
sudo apt-get install python3-pip npm gulp mysql-client-core-5.7
sudo npm install -g gulp-cli
npm install gulp -D
pip install -r requirements.txt --user
npm install
gulp build
```

If you want TinyMCE uploads to work, don't forget to run
```
python manage.py collectstatic
```