import click
from flask.cli import with_appcontext
from .extensions import db
from .models import Admin

@click.command("init-db")
@with_appcontext
def init_db():
    """Create tables in the configured MySQL database (empty data store)."""
    if not db.engine.url.drivername.startswith("mysql"): raise click.ClickException("DATABASE_URL must use a MySQL driver, for example mysql+pymysql://...")
    db.engine.connect().close(); db.create_all(); click.echo("MySQL tables created; no records were seeded.")

@click.command("create-admin")
@click.option("--username", prompt=True)
@click.password_option()
@with_appcontext
def create_admin(username, password):
    if len(password)<12: raise click.ClickException("Use an administrator password of at least 12 characters.")
    if Admin.query.filter_by(username=username).first(): raise click.ClickException("That username already exists.")
    user=Admin(username=username); user.set_password(password); db.session.add(user); db.session.commit(); click.echo("Administrator created.")

def register(app): app.cli.add_command(init_db); app.cli.add_command(create_admin)
