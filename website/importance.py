from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sqlalchemy import and_

from website.models import Player, PlayerStat, Stat


def calc_stat_importance(selected_position):
    """

    This function calculates the importance of various statistics in predicting player market value
    using a RandomForestRegressor model. It retrieves player data and their corresponding statistics
    from the database, trains the model, and determines the feature importances.

    Parameters:
    - selected_position (str): The selected player position for which the importance of
      stats is calculated for.

    Returns:
    - feature_importances (dict): A dictionary containing the importance scores of each statistic
      for predicting player market value.
    - player_ids (list): A list of player IDs used in the analysis.
    - player_names (list): A list of player names corresponding to the player IDs.

    """




    # All player queries who have
    # - correct position
    # - Have stats in PlayerStat

    player_queries = Player.query.filter(and_(Player.position == selected_position,
                                              Player.id.in_(p_id[0] for p_id in
                                                            PlayerStat.query.with_entities(
                                                                PlayerStat.player_id).all()))).all()

    player_ids = [player.id for player in player_queries]

    player_names = [player.name for player in player_queries]

    # Determine all relevant stats for position and puts in list
    stat_ids = [stat.stat_id for stat in PlayerStat.query.filter(PlayerStat.player_id == player_ids[0]).all()]

    stat_labels = [stat.label for stat in Stat.query.filter(Stat.id.in_(stat_ids)).all()]

    # Prepare data for model training
    x = []  # Features
    y = []  # Target variable (e.g., market_value)

    for player_id in player_ids:
        # Extract features (stat values) for each player
        stats = PlayerStat.query.filter(PlayerStat.player_id == player_id).all()
        features = [stat.value for stat in stats]
        # Accounting for GK stats
        x.append(features[:4] + features[5:] if len(features) == 13 else features)

        # Extract target variable
        target_variable = Player.query.get(player_id).market_value
        y.append(target_variable)

    # Split features and target variables into train and test sets.
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    # Create the random forest based on given parameters.
    regressor = RandomForestRegressor(n_estimators=100, random_state=42)

    # Create the model and train on input data.
    regressor.fit(x_train, y_train)

    # Feature importance
    feature_importances = dict(zip(stat_labels, regressor.feature_importances_))
    print(feature_importances)

    return feature_importances, player_ids, player_names