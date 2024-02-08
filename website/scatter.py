import pandas as pd
from flask import Blueprint, render_template, request
import plotly.express as px

from sqlalchemy import and_

from .models import Player, PlayerStat, Stat

scatter = Blueprint('scatter', __name__)

# Scatter chart route
@scatter.route('/scatter')
def scatter_chart():

    # Inputs
    position = request.args.get('position', 'Centre-Forward')
    x_stat = request.args.get('x_stat', 'npxG: Non-Penalty xG')
    y_stat = request.args.get('y_stat', 'Non-Penalty Goals')

    x_id = Stat.query.filter(Stat.label == x_stat).first().id
    y_id = Stat.query.filter(Stat.label == y_stat).first().id

    # Basic info of each relevant player within position
    player_queries = Player.query.filter(and_(Player.position == position,
                                              Player.id.in_(p_id[0] for p_id in PlayerStat.query.with_entities(
                                                  PlayerStat.player_id).all()))).all()

    player_ids = [player.id for player in player_queries]
    player_names = [player.name for player in player_queries]
    player_ages = [player.age for player in player_queries]

    # Values of x stat for each player
    x_values = PlayerStat.query.filter(and_(PlayerStat.stat_id == x_id,
                                            PlayerStat.player_id.in_(player_ids))).order_by(PlayerStat.player_id).all()
    x_values = [float(x.value.rstrip('%')) if isinstance(x.value, str) else x.value for x in x_values]

    # Values of y stat for each player
    y_values = PlayerStat.query.filter(and_(PlayerStat.stat_id == y_id,
                                            PlayerStat.player_id.in_(player_ids))).order_by(PlayerStat.player_id).all()
    y_values = [float(y.value.rstrip('%')) if isinstance(y.value, str) else y.value for y in y_values]

    # Retrieval of market values
    mk_values = [player.market_value for player in Player.query.filter(
        Player.id.in_(player_ids)).order_by(
        Player.id).all()]

    df = pd.DataFrame({
        x_stat: x_values,
        y_stat: y_values,
        "Name": player_names,
        'Age': player_ages,
        'Value': mk_values
    })

    fig = px.scatter(df, x=x_stat, y=y_stat, size="Value", trendline="ols", hover_name="Name",
                     color='Age', color_continuous_scale='Viridis')

    # Adjust the size of the figure
    fig.update_layout(width=720, height=720)

    fig.update_xaxes(range=[0, 1.1 * max(x_values)])
    fig.update_yaxes(range=[0, 1.1 * max(y_values)])

    fig2 = px.histogram(df, x=x_stat, nbins=64, marginal='rug',
                        title=f'{position}')

    fig2.update_layout(width=600, height=600)

    scatter_chart_html = fig.to_html(full_html=False)
    distplot_html = fig2.to_html(full_html=False)

    # Fetch unique values for position, x_stat, and y_stat
    positions = list(dict.fromkeys([player.position for player in Player.query.distinct(Player.position)]))
    stats = [stat.label for stat in Stat.query.distinct(Stat.label)][:19]
    gk_stats = [stat.label for stat in Stat.query.distinct(Stat.label)][19:]

    return render_template('scatter.html', scatter_chart=scatter_chart_html, distplot=distplot_html,
                           positions=positions, x_stats=stats, y_stats=stats, gk_stats=gk_stats, selected_position=position,
                           selected_x_stat=x_stat, selected_y_stat=y_stat)
