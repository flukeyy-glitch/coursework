from flask import Blueprint, render_template, request
import plotly.graph_objects as go

from sqlalchemy import and_

from .importance import calc_stat_importance
from .models import Player, PlayerStat, Stat

# Create Flask blueprint for radar page
radar = Blueprint('radar', __name__)


@radar.route('/radar')
def radar_chart():
    """

    This function renders the radar chart page using the 'radar.html' template. It retrieves data
    on player stats from the database and calls a function that calculates features importance for the
    selected position. This data is passed into a function that creates the radar chart.

    Returns:
    HTML: Rendered HTML template for the radar chart page.
    """


    # All positions
    positions = list(dict.fromkeys([player.position for player in Player.query.distinct(Player.position)]))

    # Aspirational objective
    positions.remove("Goalkeeper")

    # Get selected names from the query parameters
    selected_position = request.args.get('position', 'Right Winger')

    # Importance of each feature and the names found with stats in the given position
    feature_importances, player_ids, player_names = calc_stat_importance(selected_position)
    player1 = request.args.get('player1', 'Bukayo Saka')
    player2 = request.args.get('player2', 'Phil Foden')

    # Function to generate the radar chart given names
    radar_chart1 = generate_radar_chart(player1, player2, feature_importances, player_ids)

    return render_template('radar.html', radar_chart=radar_chart1,
                           positions=positions, selected_position=selected_position, names=player_names,
                           player1=player1, player2=player2)


def generate_radar_chart(player1, player2, feature_importance_dict, player_ids):
    """

    This function generates a radar chart comparing two players based on the top 5 feature importance
    scores calculated from the RandomForestRegressor model. It uses Plotly graph objects to create
    the radar chart.

    Parameters:
    - player1 (str): The name of the first player.
    - player2 (str): The name of the second player.
    - feature_importance_dict (dict): A dictionary containing the importance scores of each stat
      for predicting player market value.
    - player_ids (list): A list of player IDs used in the analysis.

    Returns:
    HTML: Rendered HTML for the radar chart.
    """

    # The top 5 most important stats based on calculated feature importance
    top_stats = sorted(feature_importance_dict, key=lambda k: feature_importance_dict[k], reverse=True)[:5]

    # IDs of these stats
    top_stat_ids = [Stat.query.filter_by(label=stat_label).first().id for stat_label in top_stats]

    # IDs of both the selected players
    player_1_id = Player.query.filter_by(name=player1).first().id
    player_2_id = Player.query.filter_by(name=player2).first().id

    max_values = {}
    for stat_id in top_stat_ids:
        # Loop to find the max value of each stat in the selected position, used as the outer bound on the radar chart
        max_value = PlayerStat.query.filter(and_(PlayerStat.player_id.in_(player_ids),
                                                 PlayerStat.stat_id == stat_id)).order_by(
            PlayerStat.value.desc()).first().value
        max_values[stat_id] = max_value if isinstance(max_value, str) else max_value

    # List of each players' stat values
    player_1_values = [
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value
        if isinstance(PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value, str) else
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_1_id, PlayerStat.stat_id == stat_id)).first().value
        for stat_id in top_stat_ids
    ]

    player_2_values = [
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value
        if isinstance(PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value, str) else
        PlayerStat.query.filter(and_(PlayerStat.player_id == player_2_id, PlayerStat.stat_id == stat_id)).first().value
        for stat_id in top_stat_ids
    ]

    # Values scaled to percentiles of max
    player_1_values_scaled = [val / max_values[stat_id] for val, stat_id in zip(player_1_values, top_stat_ids)]
    player_2_values_scaled = [val / max_values[stat_id] for val, stat_id in zip(player_2_values, top_stat_ids)]

    fig = go.Figure()

    # Add player 1 plot
    fig.add_trace(go.Scatterpolar(
        r=player_1_values_scaled,
        theta=top_stats,
        fill='toself',
        name=player1
    ))

    # Add player 2 plot
    fig.add_trace(go.Scatterpolar(
        r=player_2_values_scaled,
        theta=top_stats,
        fill='toself',
        name=player2
    ))

    # Conversion to polar chart with radial axis
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=False
    )

    return fig.to_html(full_html=False)


