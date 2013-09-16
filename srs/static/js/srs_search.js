$(document).ready(function() {
	$(".datePicker").datepicker({
		dateFormat : "yy-mm-dd"
	});

	$(".clickme_advsearch").click(function() {
		$(".blind_advsearch").show("blind", {}, 1000);
	});
});
