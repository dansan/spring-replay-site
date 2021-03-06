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
	$(".datePicker").datepicker({
		dateFormat : "yy-mm-dd"
	});

	$(".clickme_advsearch").click(function() {
		$(".blind_advsearch").show("blind", {}, 1000);
	});
});
