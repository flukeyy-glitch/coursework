from . import db


# Generate SQLAlchemy classes for each table
class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    coefficient = db.Column(db.Integer, unique=True)
    nation = db.Column(db.String(32))


class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    age = db.Column(db.Integer)
    position = db.Column(db.String(32))
    market_value = db.Column(db.Integer)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'))


class Stat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64))


class PlayerStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    stat_id = db.Column(db.Integer, db.ForeignKey('stat.id'))
    value = db.Column(db.Integer)

