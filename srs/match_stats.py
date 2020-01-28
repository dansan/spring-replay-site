# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2018 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os.path
from collections import OrderedDict

import plotly
import plotly.graph_objs as go

from .models import TeamStats
from .SpringStatsViewer.SpringDemoFile import DemoFileReader

try:
    from typing import Dict, List, Optional, Tuple, Union
    from SpringStatsViewer.SpringDemoFile import PlayerStatistics, TeamStatistics
except ImportError:
    pass


logger = logging.getLogger(__name__)


class MatchStatsGeneration(object):
    def __init__(self, file_path):
        self.file_path = os.path.abspath(file_path)
        self.demofile = DemoFileReader(self.file_path)

    def make_teamstat_graphs(cls, teamstats):
        # type: (Dict[str, List[TeamStatistics]]) -> Dict[str, Dict[str, List[float]]]
        res = OrderedDict()  # type: Dict
        for ts_attr, label in TeamStats.graphid2label.items():
            res[ts_attr] = dict(
                (player, [getattr(s, ts_attr) for s in stats])
                for player, stats in teamstats.items()
            )
        return res

    @staticmethod
    def checkteamstatlength(demofile):  # type: (DemoFileReader) -> bool
        """
        Copied from SpringStatsViewer/SpringStatsViewer.py to not have to depend on Tix.

        Return true if the length of at least one entry in the demo file teamstats > 1, false otherwise
        """
        vlength = 0
        for p in demofile.teamstatistics:
            if len(demofile.teamstatistics[p]) > vlength:
                vlength = len(demofile.teamstatistics[p])
                if vlength > 1:
                    return True
        if vlength > 1:
            return True
        else:
            return False

    def make_stats(self):
        # type: () -> Tuple[Dict[str, Dict[str, int]], Dict[str, List[Dict[str, Union[str, List[float]]]]]]
        playerstats_res = {}  # type: Dict[str, Dict[str, int]]
        teamstats_plotly_kwargs = (
            {}
        )  # type: Dict[str, List[Dict[str, Union[str, List[float]]]]]
        if (
            self.demofile.header()
            and self.demofile.script()
            and not self.demofile.incomplete
            and not self.demofile.crashed
        ):
            playerstats = self.demofile.playerstats()
            if playerstats:
                logger.debug("** We have playerstats: {!r}".format(playerstats))
                playerstats_res = dict((k, v.__dict__) for k, v in playerstats.items())
                teamstats = self.demofile.teamstats()
                if teamstats and self.checkteamstatlength(self.demofile):
                    logger.debug("** We have teamstats.")
                    graphs = self.make_teamstat_graphs(teamstats)
                    # create x-axis units
                    teamstatperiod_in_minutes = self.demofile.teamstatperiod / 60.0
                    x_axis = [0.0]
                    a_stat = graphs.values()[0]  # type: Dict[str, List[float]]
                    a_stat_list = a_stat.values()[0]  # type: List[float]
                    for i in range(len(a_stat_list) - 1):
                        x_axis.append(x_axis[-1] + teamstatperiod_in_minutes)
                    for ts_type, stats in graphs.items():
                        plot_data_kwargs = [
                            dict(x=x_axis, y=p_stats, name=player)
                            for player, p_stats in stats.items()
                        ]  # type: List[Dict[str, Union[str, List[float]]]]
                        teamstats_plotly_kwargs[ts_type] = plot_data_kwargs
                else:
                    logger.debug("** We have NO teamstats.")
            else:
                logger.debug("** We have NO playerstats.")
        return playerstats_res, teamstats_plotly_kwargs

    @staticmethod
    def get_team_stat_plot(title, plotly_kwargs, graph_type="lines"):
        # type: (str, List[Dict[str, Union[str, List[float]]]], Optional[str]) -> str
        plot_data = [go.Scatter(mode=graph_type, **kwargs) for kwargs in plotly_kwargs]
        layout = go.Layout(
            title=title,
            autosize=True,
            # paper_bgcolor='#1c1e22',
            # plot_bgcolor='#2e3338',
            # legend = {'bgcolor': '#2e3338'},
            xaxis={"title": "minute"},
            yaxis={"title": "per second"},
        )
        return plotly.offline.plot(
            figure_or_data=go.Figure(data=plot_data, layout=layout),
            auto_open=False,
            output_type="div",
            include_plotlyjs=False,
            show_link=False,
        )
