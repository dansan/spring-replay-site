/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// http://stackoverflow.com/a/1349426
function random_text()
{
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    for( var i=0; i < 8; i++ )
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

// set name and email fields, as they are required, so browsers are happy
// we don't use those fields, we store the Django User of the logged in user anyway
// store random text in those fields, as they should be unique
$( document ).ready(function()
{
    $("#replay_comments #id_name").val(random_text() + ' ' + random_text());
    $("#replay_comments #id_email").val(random_text() + '@' + random_text() + '.' + random_text());
    $("#infolog_comments #id_name").val(random_text() + ' ' + random_text());
    $("#infolog_comments #id_email").val(random_text() + '@' + random_text() + '.' + random_text());
});
