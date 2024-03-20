# Transfermarkt data collection
from unidecode import unidecode

from . import db


def scrape_data():
    """
    Scrape data from Transfermarkt website for leagues, clubs, and players,
    and store that data into the database.

    This function iterates over several leagues, collects data for each club within
    the league, and then collects data for each player within each club.

    Data scraped:
    - League name, coefficient, and nation
    - Club name
    - Player name, age, position, and market value

    The scraped data is stored in the corresponding database tables.

    Parameters:
    None

    Returns:
    None

    """
    import requests
    from bs4 import BeautifulSoup

    from .models import League, Club, Player

    # Cover headers used to appear as browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/47.0.2526.106 Safari/537.36'}

    # URLS of leagues wanted
    urls = ["https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1",
            "https://www.transfermarkt.co.uk/serie-a/startseite/wettbewerb/IT1",
            "https://www.transfermarkt.co.uk/primera-division/startseite/wettbewerb/ES1"
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

            # Take ID of club's league
            league_id = League.query.filter_by(name=league_name).first().id

            # Instantiate club record
            club = Club(name=club_name, league_id=league_id)

            # Commit the club to the database
            db.session.merge(club)
            db.session.commit()


            # Lists of players attributes within the club
            # Name
            names_html = soup.find_all('td', {"class": 'hauptlink'})
            names = [unidecode(n.text.strip()) for n in names_html if n.text[-1] == "\n"]

            # Age
            age_td = soup.select("td.zentriert")
            age = [a for a in age_td if a.text != "" and len(a.text) == 2 and "div" not in str(a)]
            ages = [int(a.text) for a in age]

            # Position
            position_td = soup.select("table.inline-table tr:nth-of-type(2)")
            positions = [position.get_text(strip=True) for position in position_td]

            # Market Value
            values_html = soup.find_all('td', {"class": 'rechts hauptlink'})

            # Take ID of club
            club_id = Club.query.filter(Club.name == club_name).first().id

            # Iterate over each player
            for name, age, position, value_html in zip(names, ages, positions, values_html):

                # Conversion from string to quantitative
                if value_html.text[-1] == "m":
                    value = round(float(value_html.text[1:-1]), 1)

                # Conversion to millions unit from thousands
                elif value_html.text[-1] == "k":
                    value = round(float(value_html.text[1:-1]) / 1000, 1)

                # Auto to 0 value if not specified
                else:
                    value = 0

                # New instance of Player
                player = Player(name=name, age=age, position=position, market_value=value, club_id=club_id)

                # Commit player to db
                db.session.merge(player)
                db.session.commit()

    print("TransferMarkt data taken")