/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

$(document).ready(function() {
	$(".clickme_winner").click(function() {
		$(".blind_winner").show("blind", {}, 0);
		$(".blind_winner_team").attr("style", "color:#deaa42");
	});
});

// work around missing possibility to adjust from
$(document).ready(function() {
    $("#id_comment").addClass("form-control");
    $("#id_comment").attr("rows", "3");
    $("#id_comment").attr("cols", "10");
    $("#id_comment").wrap('<div class="col-lg-10 col-lg-offset-2"></div>');
});
