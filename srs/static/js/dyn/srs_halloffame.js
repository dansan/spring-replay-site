/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// initialize DataTables
var tables = $( "table[id^='lbtable-']" );
for (index = 0; index < tables.length; ++index) {
	var tid = tables[ index ].id.split("-")[1];
	$( tables[ index ] ).dataTable({
	"bAutoWidth": false,
	"bLengthChange": false,
	"bFilter": false,
	"bPaginate": false,
	"bSort": false,
	"bInfo": false,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url( "hof_tbl_src", tid ),
	"aoColumnDefs": [
       {
		  "aTargets": [ 1 ],
		  "mData": 1,
		  "mRender": function ( data, type, full ) {
			  return '<a href="' + Django.url('player_detail', full[6] ) + '">' + data + '</a>';
		  }
	  }],
	});
}
