/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// initialize DataTable
var browse_table = $( "#comments-table" ).dataTable({
	"bAutoWidth": true,
	"iDisplayLength": 25,
	"aaSorting": [[ 0, "desc" ]],
	"bPaginate": true,
	"sPaginationType": "bootstrap",
	"bScrollCollapse": true,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url( "srs/comment_tbl_src$" ),
	"bRegex" : true,
	"aoColumns": [
	              { "bSearchable": false },
	              { "bSearchable": false },
	              null
	              ],
	"aoColumnDefs": [
         {
          "aTargets": [ 0 ],
	      "mData": function ( data, type, val ) {
	    	  console.log( "data:" );
	    	  console.log( data );
		  if (type === "set") {
			  data[0] = moment(data[0]);
			  return;
			  } else if (type === "display") {
				  return data[0].format( "YYYY-MM-DD HH:mm" );
			  }
		  return data[0];
		  },
		  "mRender": function ( data, type, full ) {
			  return data;
			  }
         },
         {
		  "aTargets": [ 1 ],
		  "mData": 1,
		  "mRender": function ( data, type, full ) {
			  return '<a href="' + Django.url('srs/player', full[3] ) + '">Player</a> | <a href="' + Django.url('srs/replay_by_id', full[4] ) + '">Match</a>';
			  }
         }
         ]
});
$( "div#comments-table_filter.dataTables_filter > label" ).wrapInner( '<h4></h4>' );
$( "div#comments-table_filter.dataTables_filter input" ).addClass( "form-control" );
$( "div#comments-table_length.dataTables_length > label" ).wrapInner( "<h4></h4>" );
$( "div#comments-table_length.dataTables_length select" ).addClass( "form-control" );
