# FBref data collection

def scrape_stats():
    """
    This function collects statistical data for football clubs and players from FBref.com,
    from leagues such as the Premier League, Serie A, and La Liga. It iterates
    through each league, retrieves club information, and then extracts player data for each club.
    The collected data includes player statistics such as goals, assists, passes, etc.

    Parameters:
    None

    Returns:
    None


    """
    import requests
    from bs4 import BeautifulSoup
    import re

    import time

    from fuzzywuzzy import fuzz
    from sqlalchemy import and_
    from unidecode import unidecode

    from . import db

    # Prevent IP from being blocked
    DELAY = 4

    from .models import Club, Player, Stat, PlayerStat

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/47.0.2526.106 Safari/537.36',
        'Connection': 'keep-alive'}

    urls = ["https://fbref.com/en/comps/9/stats/Premier-League-Stats",
            "https://fbref.com/en/comps/11/Serie-A-Stats",
            "https://fbref.com/en/comps/12/La-Liga-Stats"
            ]

    # Convert instances of club name that are very different from existing in database
    club_name_conversion_dict = {"Rennes": "Stade Rennais FC", "Internazionale": "Inter Milan",
                                 "Nott'ham Forest": "Nottingham Forest", "Wolves": "Wolverhampton Wanderers",
                                 "Athletic Club": "Athletic Bilbao"}

    # Iterate over each league
    for url in urls:

        # Pause used to prevent over requesting
        time.sleep(DELAY)
        page_tree = requests.get(url, headers=headers)
        soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

        # Club urls collection
        teams_table = soup.select('table.stats_table')[0]
        links = teams_table.find_all('a')

        # Collected club name from link's HREF
        initial_club_names = [link.get_text(strip=True).replace('Utd', 'United') for link in links if
                              '/squads' in link.get("href")]

        # Convert some club names which are not similar to existing in database
        club_names = []
        for club_name in initial_club_names:
            if club_name in club_name_conversion_dict.keys():
                club_names.append(club_name_conversion_dict[club_name])
            else:
                club_names.append(club_name)

        # Obtain HREF from each link
        links = [link.get("href") for link in links if '/squads/' in link.get("href")]

        # Generate full URLs with prefix
        team_urls = [f"https://fbref.com{link}" for link in links]

        # Iterate over each club
        for team_url, club in zip(team_urls, club_names):
            time.sleep(DELAY)
            page_tree = requests.get(team_url, headers=headers)
            soup = BeautifulSoup(page_tree.content, 'html.parser', from_encoding='utf-8')

            # Try except block to match club name between TransferMarkt and FBref
            try:
                # Club name is a substring of record in Club
                club_id = Club.query.filter(Club.name.like(f"%{club}%")).first().id

            except AttributeError:
                print(club)
                span_re = re.compile('<span>(.*)<\/span>')

                [club_title] = span_re.findall(str(soup.select('#meta')[0].find_all('h1')))
                pattern = re.compile(r'\d{4}-\d{4}\s(.+?)\sStats')

                # Text taken from header using {pattern} regular expression
                club_name = pattern.search(club_title).group(1)
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
                time.sleep(DELAY)
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
                labels_table = soup.select_one("table[id*=scout_summary]")
                if labels_table:
                    tbody = labels_table.find('tbody')
                    th_tags = tbody.find_all("th")
                    labels_html = [th.text for th in th_tags if len(th.text) > 1]

                    # Scrape values from each player page
                    values_html = table.find_all('td', class_='right')
                    values = [value.get_text(strip=True) for value in values_html
                              if len(value.get_text(strip=True)) > 1]

                    for label, value in zip(labels_html, values):

                        labels = db.session.query(Stat.label).all()

                        # Remove strange tuple structure from db query in labels
                        # Removes empty values
                        labels = [label[0] for label in labels if len(label[0]) > 1]

                        # Check stat doesn't exist already in Stat table
                        if label not in labels:
                            stat = Stat(label=label)

                            # Commit to DB
                            db.session.merge(stat)
                            db.session.commit()

                        # Takes id from Stat table based on label
                        stat_id = Stat.query.filter(Stat.label == label).first().id

                        # Value conversion from percentage
                        value = float(value.rstrip('%'))

                        # Avoid making duplicates
                        if not PlayerStat.query.filter(and_(PlayerStat.player_id == player_id,
                                                            PlayerStat.stat_id == stat_id)).first():
                            # Create instance in PlayerStat table
                            player_stat = PlayerStat(player_id=player_id, stat_id=stat_id, value=value)

                            # Commit player_stat
                            db.session.merge(player_stat)
                            db.session.commit()
