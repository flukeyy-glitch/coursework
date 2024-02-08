from flask import Blueprint, render_template, request
import plotly.graph_objects as go

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sqlalchemy import and_

from .models import Player, PlayerStat, Stat

radar = Blueprint('radar', __name__)


@radar.route('/radar')
def radar_chart():
    # All positions
    positions = list(dict.fromkeys([player.position for player in Player.query.distinct(Player.position)]))

    # Get selected names from the query parameters
    selected_position = request.args.get('position', 'Right Winger')

    # Importance of each feature and the names found with stats in the given position
    feature_importances, player_ids, player_names = get_stat_importance(selected_position)
    player1 = request.args.get('player1', 'Bukayo Saka')
    player2 = request.args.get('player2', 'Phil Foden')

    # Function to generate the radar chart given names
    radar_chart1 = generate_radar_chart(player1, player2, feature_importances, player_ids)

    return render_template('radar.html', radar_chart=radar_chart1,
                           positions=positions, selected_position=selected_position, names=player_names,
                           player1=player1, player2=player2)


def generate_radar_chart(player1, player2, feature_importance_dict, player_ids):
    top_stats = sorted(feature_importance_dict, key=lambda k: feature_importance_dict[k], reverse=True)[:5]
    top_stat_ids = [Stat.query.filter_by(label=stat_label).first().id for stat_label in top_stats]

    player_1_id = Player.query.filter_by(name=player1).first().id
    player_2_id = Player.query.filter_by(name=player2).first().id

    max_values = {}
    for stat_id in top_stat_ids:
        max_value = PlayerStat.query.filter(and_(PlayerStat.player_id.in_(player_ids),
                                                 PlayerStat.stat_id == stat_id)).order_by(
            PlayerStat.value.desc()).first().value
        max_values[stat_id] = float(max_value.rstrip('%')) if isinstance(max_value, str) else max_value

    player_1_values = [
        float(PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value.rstrip('%'))
        if isinstance(PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value, str) else
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value
        for stat_id in top_stat_ids
    ]

    player_2_values = [
        float(PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value.rstrip('%'))
        if isinstance(PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value, str) else
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value
        for stat_id in top_stat_ids
    ]

    player_1_values_scaled = [val / max_values[stat_id] for val, stat_id in zip(player_1_values, top_stat_ids)]
    player_2_values_scaled = [val / max_values[stat_id] for val, stat_id in zip(player_2_values, top_stat_ids)]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=player_1_values_scaled,
        theta=top_stats,
        fill='toself',
        name=player1
    ))

    fig.add_trace(go.Scatterpolar(
        r=player_2_values_scaled,
        theta=top_stats,
        fill='toself',
        name=player2
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=False
    )

    return fig.to_html(full_html=False)


def get_stat_importance(selected_position):
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
        features = [float(stat.value.rstrip('%')) if isinstance(stat.value, str) else stat.value for stat in stats]
        x.append(features[:4] + features[5:] if len(features) == 13 else features)

        # Extract target variable
        target_variable = Player.query.get(player_id).market_value
        y.append(target_variable)

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    regressor = RandomForestRegressor(n_estimators=326, random_state=42, max_depth=3,
                                      min_samples_split=2, min_samples_leaf=7)

    regressor.fit(x_train, y_train)

    # Feature importance
    feature_importances = dict(zip(stat_labels, regressor.feature_importances_))

    return feature_importances, player_ids, player_names
