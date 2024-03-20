from . import db


# Generate SQLAlchemy classes for each table
class League(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    coefficient = db.Column(db.Integer, unique=True)
    nation = db.Column(db.String(32))


class Club(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    # Foreign key
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))


class Player(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    age = db.Column(db.Integer)
    position = db.Column(db.String(32))
    market_value = db.Column(db.Integer)
    # Foreign key
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'))


class Stat(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64))


class PlayerStat(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    # Foreign key
    stat_id = db.Column(db.Integer, db.ForeignKey('stat.id'))
    value = db.Column(db.Integer)
