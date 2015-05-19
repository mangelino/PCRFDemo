	<script type="text/javascript">
	var intervalId;
	var consChart;
	var bwChart;
	var consDps = [];
	var bwDps = []; // dataPoints
	var consumed = 0;
	var MAXSTOP = 999999999;
	var AVGBW = 500;	


	window.onload = function() {
		consChart = new CanvasJS.Chart("consumption",{
			title :{
				text: "Data consumption"
			},			
			data: [{
				type: "line",
				dataPoints: consDps 
			}]
		});

		bwChart = new CanvasJS.Chart("bandwidth",{
			title :{
				text: "Bandwidth"
			},			
			data: [{
				type: "line",
				dataPoints: bwDps 
			}]
		});
	}

	var xVal = 0;
	var yVal;
	var stopX = MAXSTOP;	
	var averageBw = 200;
	var updateInterval = 20;
	var dataLength = 500; // number of dataPoints visible at any point

	var updateChart = function (count, bw) {
		count = count || 1;
		// count is number of times loop runs to generate random dataPoints.
		var delta= Math.round(bw/5 + Math.random() *(-bw));


		for (var j = 0; j < count; j++) {	
			yVal = bw +  delta;
			if (consumed > 500000) {
				if (yVal > 50) {
					yVal = 50;

				}
				if (stopX == MAXSTOP) {
					stopX = xVal;
				}
			}
			if (yVal<0) {
					yVal = 0;
				}
			bwDps.push({
				x: xVal,
				y: yVal
			});

			consumed = consumed + yVal;
			consDps.push({
				x: xVal,
				y: consumed
			});

			xVal++;
			if (xVal-stopX > dataLength) {
				clearInterval(intervalId);
			}
		};
		if (bwDps.length > dataLength)
		{
			bwDps.shift();				
		}

			

		if (consDps.length > dataLength)
		{
			consDps.shift();				
		}
		consChart.render();
		bwChart.render();

	};
	

	function start() {
		stopX = MAXSTOP;
		if (intervalId)
			clearInterval(intervalId); 

		// generates first set of dataPoints
		updateChart(dataLength,0); 
		consumed = 0;

		// update chart after specified time. 
		intervalId = setInterval(function(){updateChart(1, AVGBW)}, updateInterval); 
	}

	function stop() {
		// update chart after specified time. 
		clearInterval(intervalId); 
	}

	function pause() {
		if (intervalId) {
			clearInterval(intervalId);
			intervalId = null;
		} else {
			intervalId = setInterval(function(){updateChart(1, AVGBW)}, updateInterval);
		}
		
	}
	</script>
	<script type="text/javascript" src="/assets/script/canvasjs.min.js"></script>