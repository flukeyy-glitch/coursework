from flask import Blueprint, render_template

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sqlalchemy import distinct, and_

from .models import Player, PlayerStat, Stat

import numpy as np

importance = Blueprint('importance', __name__)


@importance.route('/importance')
def stat_importance():
    # List of all possible positions
    positions = [position[0] for position in Player.query.with_entities(distinct(Player.position)).all()]

    total_error = 0
    # Weights for every individual position
    for position in positions:
        # All player queries who have
        # - correct position
        # - Have stats in PlayerStat
        print(f'POSITION: {position}')

        player_queries = Player.query.filter(and_(Player.position == position,
                                                  Player.id.in_(p_id[0] for p_id in
                                                                PlayerStat.query.with_entities(
                                                                    PlayerStat.player_id).all()))).all()

        player_ids = [player.id for player in player_queries]

        # player_names = [player.name for player in player_queries]

        # Determine all relevant stats for position and puts in list
        stat_ids = [stat.stat_id for stat in PlayerStat.query.filter(PlayerStat.player_id == player_ids[0]).all()]

        stat_labels = [stat.label for stat in Stat.query.filter(Stat.id.in_(stat_ids)).all()]

        # Prepare data for model training
        x = []  # Features
        y = []  # Target variable (e.g., market_value)

        for player_id in player_ids:
            # Extract features (stat values) for each player
            stats = PlayerStat.query.filter(PlayerStat.player_id == player_id).all()
            features = [float(stat.value.rstrip('%')) if isinstance(stat.value, str) else stat.value for stat in stats]
            x.append(features[:4] + features[5:] if len(features) == 13 else features)

            # Extract target variable
            target_variable = Player.query.get(player_id).market_value
            y.append(target_variable)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

        regressor = RandomForestRegressor(n_estimators=326, random_state=42, max_depth=3,
                                          min_samples_split=2, min_samples_leaf=9)

        regressor.fit(x_train, y_train)

        predictions = regressor.predict(x_test)

        mse = mean_squared_error(y_test, predictions)
        print(f'Mean Squared Error: {mse}')
        total_error += mse

        # Feature importance
        feature_importances = regressor.feature_importances_
        print('Feature Importances:')

        for stat_label, importance_ in zip(stat_labels, feature_importances):
            print(f'{stat_label}: {int(importance_ * 100)}%')

    return render_template('importance.html')
