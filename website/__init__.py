from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path

# Initiation of SQLAlchemy as db
db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():
    """
    Create and configure the Flask app.

    Returns:
        The Flask app.
    """
    from .models import League, Club, Player, Stat, PlayerStat

    # Configurating Flask app and database
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '3723523585828935985'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    # Import blueprints of HTML pages
    from .home import home
    from .radar import radar
    from .scatter import scatter

    # Register blueprints in Flask app
    app.register_blueprint(home, url_prefix='/')
    app.register_blueprint(radar, url_prefix='/')
    app.register_blueprint(scatter, url_prefix='/')

    create_database(app)

    return app


def create_database(app):
    """
    Create the database if it doesn't exist and populate it with initial data.

    Args:
        app (Flask): The Flask application.
    """
    from .transfermarkt import scrape_data
    from .fbref import scrape_stats

    with app.app_context():
        # If database doesn't exist
        if not path.exists('instance/' + DB_NAME):
            print('Database needs to be built')
            # Create database schema
            db.create_all()
            scrape_data()
            scrape_stats()
        print('Database Online')
