## Running in production mode

The recommended solution is to use nginx-gunicorn-docker setup, which we provide for out of the box if you run the following command.

**NOTE** Before running the command, please replace the values within the angle brackets (<>) in the `.env.prod` file! Make sure none of those values are published anywhere, since they will compromise the security of your Textinator instance!

The easiest way to start the server is by running `sh tools/start_prod.sh` after cloning the repository. This command will effectively do the following:

```bash
cd Textinator
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up
```

Now if you go to `http://localhost:1337`, you should see Textinator's main page.

Note that this command will build the Docker image only once and thus will copy the code only once. If you've some changes to the code and want to include them, you'll need to add a `--build` flag at the end of the command above.

To stop container, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml stop`

To run container again, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d`

To stop container AND take down the DB, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml down -v`

### Exposing the ports and HTTPS

By default Textinator's port is `1337` and it is exposed only to the localhost and all requests are handled as HTTP to not impose any particular SSL certificate for handling HTTPS requests. To handle HTTPS, you'll need to set it up on your own server and then just reverse proxy to `http://localhost:1337`.

### Serve on a custom (sub)domain

It's absolutely possible to use custom domain, but first you need to let Textinator know that your domain is allowed. You can do this by adding your domain(s) to the `DJANGO_ALLOWED_HOSTS` variable in the `.env.prod` file (note that the list of domains is space-separated).

### Serve on a custom URL

If you have a server with a domain that hosts multiple applications, but you're unable to order subdomains for it, you might want to consider hosting Textinator on a specific URL. This is possible and requires the following steps (for this example we'll assume your custom URL is `mydomain.com/textinator` and we assume that you've already let Textinator know that `mydomain.com` is allowed).

1.  Change `ROOT_URLPATH` to `textinator/` (note that the trailing `/` is **mandatory**) in the `.env.prod` file.
2.  Change `location /static/` to `location /textinator/static/` and `location /media/` to `location /textinator/media/` in the `nginx/nginx.conf` file.
3.  Re-route all other URLs:
    *   If you host Textinator as a part of another server, then let `/textinator` point to `http://localhost:1337`
    *   If you host a standalone instance of Textinator, change `location /` to `location /textinator/` in the `nginx/nginx.conf`

### Database backup

We recommend to schedule a cron job to make a backup of the database. For example, making a backup every day at 16:00 would translate into the following cron task (assuming you want to save your dumps into `/home/your_user/textinator_dumps` folder of your server):

`0 16 * * * docker exec -i textinator_db_1 pg_dump -U textinator > /home/your_user/textinator_dumps/$(date +\%s).sql`

**NOTE** Escaping (putting `\` before) `%s` is mandatory, since cron interprets `%` as a newline character otherwise.
