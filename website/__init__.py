from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from os import path

import time

# Necessary to merge based on names using special characters
from unidecode import unidecode

# Used in player name comparison
from fuzzywuzzy import fuzz

# Initiation of SQLAlchemy database
db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():

    from .models import League, Club, Player, Stat, PlayerStat

    # Configurating Flask app and database
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '3723523585828935985'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    # Import blueprints of HTML pages
    from .views import views
    from .radar import radar
    from .scatter import scatter
    from .importance import importance

    # Register blueprints in Flask app
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(radar, url_prefix='/')
    app.register_blueprint(scatter, url_prefix='/')
    app.register_blueprint(importance, url_prefix='/')

    create_database(app)

    return app


def create_database(app):
    with app.app_context():
        # If database doesn't exist
        if not path.exists('instance/' + DB_NAME):
            print('Database needs to be built')
            # Create database schema
            db.create_all()
            scrape_data()
            scrape_stats()
        print('Database Online')


# Transfermarkt data collection
def scrape_data():
    import requests
    from bs4 import BeautifulSoup

    from .models import League, Club, Player, Stat, PlayerStat

    # Cover headers used to appear as browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/47.0.2526.106 Safari/537.36'}

    # URLS of leagues wanted
    urls = ["https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1",
            "https://www.transfermarkt.co.uk/serie-a/startseite/wettbewerb/IT1",
            "https://www.transfermarkt.co.uk/primera-division/startseite/wettbewerb/ES1",
            "https://www.transfermarkt.co.uk/ligue-1/startseite/wettbewerb/FR1",
            "https://www.transfermarkt.co.uk/bundesliga/startseite/wettbewerb/L1",
            "https://www.transfermarkt.co.uk/eredivisie/startseite/wettbewerb/NL1",
            "https://www.transfermarkt.co.uk/liga-portugal/startseite/wettbewerb/PO1",
            "https://www.transfermarkt.co.uk/jupiler-pro-league/startseite/wettbewerb/BE1"
            ]

    # Iterate over each league
    for url in urls:
        page_tree = requests.get(url, headers=headers)
        soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

        # League attributes
        league_name = soup.find('h1',
                                class_='data-header__headline-wrapper '
                                       'data-header__headline-wrapper--oswald').get_text().strip()

        coefficient = int(soup.find('a', href='/uefa/5jahreswertung/statistik').get_text()[0])
        nation = soup.find('span', class_='data-header__club').find('a').get_text().strip()

        # Create instance of League
        league = League(name=league_name, coefficient=coefficient, nation=nation)

        # Links collected from each club in the league
        club_links = soup.select("table", {"class": "items"})[1].find_all('a')
        club_links = [link.get("href") for link in club_links if '/kader/verein/' in link.get("href")]
        club_links = list(dict.fromkeys([f"https://transfermarkt.co.uk{link}" for link in club_links]))

        # Commit the league to the database
        db.session.merge(league)
        db.session.commit()

        # Iterate over each club
        for club in club_links:
            page_tree = requests.get(club, headers=headers)
            soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

            # Club attributes
            club_name = soup.find('h1',
                                  class_='data-header__headline-wrapper '
                                         'data-header__headline-wrapper--oswald').get_text().strip()

            club_id = Club.query.filter(Club.name == club_name).first().id

            league_id = League.query.filter_by(name=league_name).first().id
            club = Club(name=club_name, league_id=league_id)

            # Commit the club to the database
            db.session.merge(club)
            db.session.commit()

            all_html = soup.find_all('td', {"class": 'hauptlink'})

            # Lists of players attributes within the club
            # Name
            names = [unidecode(n.text.strip()) for n in all_html if n.text[-1] == "\n"]

            # Age
            age_td = soup.select("td.zentriert")
            age = [a for a in age_td if a.text != "" and len(a.text) == 2 and "div" not in str(a)]
            ages = [int(a.text) for a in age]

            # Position
            position_td = soup.select("table.inline-table tr:nth-of-type(2)")
            positions = [position.get_text(strip=True) for position in position_td]

            # Market Value
            values_html = soup.find_all('td', {"class": 'rechts hauptlink'})

            # Iterate over each player
            for name, age, position, value_html in zip(names, ages, positions, values_html):

                # Conversion from string to quantative
                if value_html.text[-1] == "m":
                    value = round(float(value_html.text[1:-1]), 1)

                # Conversion to millions unit from thousands
                elif value_html.text[-1] == "k":
                    value = round(float(value_html.text[1:-1]) / 1000, 1)

                # Auto to 0 value if not specified
                else:
                    value = 0

                player = Player(name=name, age=age, position=position, market_value=value, club_id=club_id)

                # Commit player to db
                db.session.merge(player)
                db.session.commit()

# FBref data collection
def scrape_stats():
    import requests
    from bs4 import BeautifulSoup
    import re

    from .models import League, Club, Player, Stat, PlayerStat

    # Prevent IP from being blocked
    delay = 3.5

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/47.0.2526.106 Safari/537.36',
        'Connection': 'keep-alive'}

    urls = ["https://fbref.com/en/comps/9/stats/Premier-League-Stats",
            "https://fbref.com/en/comps/11/Serie-A-Stats",
            "https://fbref.com/en/comps/12/La-Liga-Stats",
            "https://fbref.com/en/comps/13/Ligue-1-Stats",
            "https://fbref.com/en/comps/20/Bundesliga-Stats",
            "https://fbref.com/en/comps/23/stats/Eredivisie-Stats",
            "https://fbref.com/en/comps/32/stats/Primeira-Liga-Stats",
            "https://fbref.com/en/comps/37/Belgian-Pro-League-Stats"
            ]

    # Iterate over each league
    for url in urls:

        # Pause used to prevent over requesting
        time.sleep(delay)
        page_tree = requests.get(url, headers=headers)
        soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

        # Club urls collection
        teams_table = soup.select('table.stats_table')[0]
        links = teams_table.find_all('a')
        club_names = [link.get_text(strip=True).replace('Utd', 'United') for link in links if '/squads' in link.get("href")]
        links = [link.get("href") for link in links if '/squads/' in link.get("href")]

        team_urls = [f"https://fbref.com{link}" for link in links]

        # Iterate over each club
        for team_url, club in zip(team_urls, club_names):
            time.sleep(delay)
            page_tree = requests.get(team_url, headers=headers)
            soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

            # Try except block to match club name between TransferMarkt and FBref
            try:
                club_id = Club.query.filter(Club.name.like(f"%{club}%")).first().id

            except AttributeError:
                span_re = re.compile('<span>(.*)<\/span>')

                [club_title] = span_re.findall(str(soup.select('#meta')[0].find_all('h1')))
                pattern = re.compile(r'\d{4}-\d{4}\s(.+?)\sStats')

                club_name = pattern.search(club_title).group(1)
                print(club_name)
                try:
                    club_id = Club.query.filter(Club.name.like(f'%{club_name}%')).first().id

                except AttributeError:
                    clubs = Club.query.all()
                    for db_club in clubs:

                        # Match based on similar strings
                        if fuzz.ratio(club_name, db_club.name) >= 90:
                            club_id = Club.query.filter(Club.name == db_club.name).first().id

            # Player url collection
            teams_table = soup.select('table.stats_table')[0]
            links = teams_table.find_all('a')
            links = [link.get("href") for link in links if '/players/' in link.get("href")]
            links = [link for link in links if '/matchlogs/' not in link]

            player_urls = [f"https://fbref.com{link}" for link in links]

            # Iterate over each player
            for player_url in player_urls:
                time.sleep(delay)
                page_tree = requests.get(player_url, headers=headers)
                soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

                # Player attributes
                # Name
                name = unidecode(str(soup.select('#meta')[0].find_all('h1')))

                span_re = re.compile('<span>(.*)<\/span>')
                [name] = span_re.findall(name)

                # Aims to match names and merge
                try:
                    player_id = Player.query.filter(and_(Player.name == name), Player.club_id == club_id).first().id

                except AttributeError:
                    continue

                try:
                    table = soup.find('table').find('tbody')

                except ValueError:
                    continue

                except AttributeError:
                    continue

                # Scrape stat labels from each player page
                labels_html = table.find_all('th')
                labels_html = [label.get_text(strip=True) for label in labels_html
                               if len(label.get_text(strip=True)) > 1]

                # Removes unwanted dates
                labels_html = [label for label in labels_html if label[0].isalpha()]

                # Scrape values from each player page
                values_html = table.find_all('td', class_='right')
                values_html = [value.get_text(strip=True) for value in values_html
                               if len(value.get_text(strip=True)) > 1]

                for label, value in zip(labels_html, values_html):

                    labels = db.session.query(Stat.label).all()

                    # Remove strange tuple structure from db query in labels
                    # Removes empty values
                    labels = [label[0] for label in labels if len(label[0]) > 1]

                    # Check stat doesn't exist already in Stat table
                    # Used in building Stat table - 32 is number of total stats
                    if label not in labels and len(labels) < 32:
                        stat = Stat(label=label)

                        # Commit to DB
                        db.session.merge(stat)
                        db.session.commit()

                    # Takes id from Stat table based on label
                    stat_id = Stat.query.filter(Stat.label == label).first().id

                    # Avoid making duplicates
                    if not PlayerStat.query.filter(and_(PlayerStat.player_id == player_id,
                                                        PlayerStat.stat_id == stat_id)).first():

                        # Create instance in PlayerStat table
                        player_stat = PlayerStat(player_id=player_id, stat_id=stat_id, value=value)

                        # Commit player_stat
                        db.session.merge(player_stat)
                        db.session.commit()
